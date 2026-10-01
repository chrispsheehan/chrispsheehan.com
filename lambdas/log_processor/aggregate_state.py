from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from typing import Any

from botocore.exceptions import ClientError

try:
    from .database_reader import build_visitor_tracker_from_database
    from .ledger import is_not_found
    from .output_writer import OUTPUT_PREFIX
except ImportError:
    from database_reader import build_visitor_tracker_from_database
    from ledger import is_not_found
    from output_writer import OUTPUT_PREFIX


AGGREGATE_PREFIX = f"{OUTPUT_PREFIX}/requests/_aggregates"
AGGREGATE_STATE_KEY = f"{AGGREGATE_PREFIX}/state.json"
DAILY_VISITORS_PREFIX = f"{AGGREGATE_PREFIX}/daily-visitors/"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AggregateState:
    daily_visits: dict[str, int]


def update_aggregate_state(
    s3_client: Any,
    bucket_name: str,
    new_records_by_date: dict[str, list[dict[str, Any]]],
) -> AggregateState:
    state = read_aggregate_state(s3_client, bucket_name)
    if state is None:
        logger.info("Aggregate state missing; bootstrapping from historical request records")
        state = bootstrap_aggregate_state(s3_client, bucket_name)
    if not new_records_by_date:
        return state

    daily_visits = dict(state.daily_visits)
    for date, records in sorted(new_records_by_date.items()):
        visitors = read_daily_visitors(
            s3_client,
            bucket_name,
            date,
            required=date in daily_visits,
        )
        visitors.update(
            record["viewer_ip"]
            for record in records
            if record.get("viewer_ip")
        )
        write_daily_visitors(s3_client, bucket_name, date, visitors)
        daily_visits[date] = len(visitors)

    updated = AggregateState(daily_visits=daily_visits)
    write_aggregate_state(s3_client, bucket_name, updated)
    logger.info(
        "Updated aggregate state touched_dates=%s tracked_dates=%s total_visits=%s",
        len(new_records_by_date),
        len(updated.daily_visits),
        sum(updated.daily_visits.values()),
    )
    return updated


def read_aggregate_state(s3_client: Any, bucket_name: str) -> AggregateState | None:
    payload = read_json_object(s3_client, bucket_name, AGGREGATE_STATE_KEY)
    if payload is None:
        return None

    daily_visits = payload.get("daily_visits")
    if not isinstance(daily_visits, dict):
        raise ValueError(f"Invalid aggregate state at s3://{bucket_name}/{AGGREGATE_STATE_KEY}")

    return AggregateState(
        daily_visits={str(date): int(count) for date, count in daily_visits.items()}
    )


def bootstrap_aggregate_state(s3_client: Any, bucket_name: str) -> AggregateState:
    visitor_tracker, _ = build_visitor_tracker_from_database(s3_client, bucket_name)
    for date, visitors in sorted(visitor_tracker.items()):
        write_daily_visitors(s3_client, bucket_name, date, visitors)

    state = AggregateState(
        daily_visits={date: len(visitors) for date, visitors in visitor_tracker.items()}
    )
    write_aggregate_state(s3_client, bucket_name, state)
    logger.info(
        "Bootstrapped aggregate state tracked_dates=%s total_visits=%s",
        len(state.daily_visits),
        sum(state.daily_visits.values()),
    )
    return state


def daily_visitors_key(date: str) -> str:
    return f"{DAILY_VISITORS_PREFIX}date={date}.json"


def read_daily_visitors(
    s3_client: Any,
    bucket_name: str,
    date: str,
    *,
    required: bool,
) -> set[str]:
    key = daily_visitors_key(date)
    payload = read_json_object(s3_client, bucket_name, key)
    if payload is None:
        if required:
            raise ValueError(f"Missing daily visitor state at s3://{bucket_name}/{key}")
        return set()

    visitors = payload.get("viewer_ips")
    if not isinstance(visitors, list):
        raise ValueError(f"Invalid daily visitor state at s3://{bucket_name}/{key}")
    return {str(visitor) for visitor in visitors}


def write_daily_visitors(
    s3_client: Any,
    bucket_name: str,
    date: str,
    visitors: set[str],
) -> None:
    write_json_object(
        s3_client,
        bucket_name,
        daily_visitors_key(date),
        {"date": date, "viewer_ips": sorted(visitors)},
    )


def write_aggregate_state(
    s3_client: Any,
    bucket_name: str,
    state: AggregateState,
) -> None:
    write_json_object(
        s3_client,
        bucket_name,
        AGGREGATE_STATE_KEY,
        {
            "version": 1,
            "daily_visits": dict(sorted(state.daily_visits.items())),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def read_json_object(s3_client: Any, bucket_name: str, key: str) -> dict[str, Any] | None:
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
    except ClientError as exc:
        if is_not_found(exc):
            return None
        raise

    body = response["Body"]
    try:
        content = body.read()
    finally:
        close = getattr(body, "close", None)
        if close is not None:
            close()

    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return json.loads(content)


def write_json_object(
    s3_client: Any,
    bucket_name: str,
    key: str,
    payload: dict[str, Any],
) -> None:
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(payload, separators=(",", ":"), sort_keys=True),
        ContentType="application/json",
    )
