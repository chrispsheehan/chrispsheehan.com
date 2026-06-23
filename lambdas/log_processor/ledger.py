from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Any

from botocore.exceptions import ClientError

try:
    from .cloudfront_logs import LogObject
except ImportError:
    from cloudfront_logs import LogObject


PROCESSING_LEASE_SECONDS = 15 * 60
LOCKS_PREFIX = "data/log-processor/locks/"


@dataclass(frozen=True)
class LockClaim:
    object_id: str
    lock_key: str
    etag: str | None


def utc_timestamp(moment: datetime | None = None) -> str:
    return (moment or datetime.now(timezone.utc)).isoformat()


def object_id(bucket_name: str, key: str, etag: str) -> str:
    source = f"{bucket_name}\0{key}\0{etag}"
    return sha256(source.encode("utf-8")).hexdigest()


def lock_key(claimed_object_id: str) -> str:
    return f"{LOCKS_PREFIX}{claimed_object_id}.json"


def claim_log_object(
    s3_client: Any,
    database_bucket_name: str,
    source_bucket_name: str,
    log_object: LogObject,
) -> LockClaim | None:
    claimed_object_id = object_id(source_bucket_name, log_object.key, log_object.etag)
    key = lock_key(claimed_object_id)
    claimed_at = datetime.now(timezone.utc)
    body = lock_body(
        claimed_object_id,
        source_bucket_name,
        log_object,
        status="processing",
        claimed_at=claimed_at,
    )

    try:
        response = put_lock_object(
            s3_client,
            database_bucket_name,
            key,
            body,
            if_none_match="*",
        )
        return LockClaim(claimed_object_id, key, response_etag(response))
    except ClientError as exc:
        if not is_precondition_failed(exc):
            raise

    existing = read_lock_object(s3_client, database_bucket_name, key)
    if existing is None:
        return None

    current_body, current_etag = existing
    if not can_reclaim(current_body, claimed_at):
        return None

    try:
        response = put_lock_object(
            s3_client,
            database_bucket_name,
            key,
            body,
            if_match=current_etag,
        )
    except ClientError as exc:
        if is_precondition_failed(exc):
            return None
        raise

    return LockClaim(claimed_object_id, key, response_etag(response))


def mark_complete(
    s3_client: Any,
    database_bucket_name: str,
    claim: LockClaim,
    record_count: int,
    output_keys: list[str],
) -> None:
    body = {
        "object_id": claim.object_id,
        "status": "complete",
        "processed_at": utc_timestamp(),
        "record_count": record_count,
        "output_keys": output_keys,
    }
    put_claim_update(s3_client, database_bucket_name, claim, body)


def mark_failed(
    s3_client: Any,
    database_bucket_name: str,
    claim: LockClaim,
    exc: Exception,
) -> None:
    body = {
        "object_id": claim.object_id,
        "status": "failed",
        "failed_at": utc_timestamp(),
        "error": str(exc)[:1000],
    }
    put_claim_update(s3_client, database_bucket_name, claim, body)


def lock_body(
    claimed_object_id: str,
    source_bucket_name: str,
    log_object: LogObject,
    *,
    status: str,
    claimed_at: datetime,
) -> dict[str, Any]:
    return {
        "object_id": claimed_object_id,
        "source_bucket": source_bucket_name,
        "source_key": log_object.key,
        "source_etag": log_object.etag,
        "source_last_modified": log_object.last_modified,
        "source_size": log_object.size,
        "status": status,
        "claimed_at": utc_timestamp(claimed_at),
        "processing_expires_at": utc_timestamp(
            claimed_at + timedelta(seconds=PROCESSING_LEASE_SECONDS)
        ),
    }


def put_claim_update(
    s3_client: Any,
    database_bucket_name: str,
    claim: LockClaim,
    body: dict[str, Any],
) -> None:
    try:
        put_lock_object(
            s3_client,
            database_bucket_name,
            claim.lock_key,
            body,
            if_match=claim.etag,
        )
    except ClientError as exc:
        if is_precondition_failed(exc):
            return
        raise


def put_lock_object(
    s3_client: Any,
    bucket_name: str,
    key: str,
    body: dict[str, Any],
    *,
    if_none_match: str | None = None,
    if_match: str | None = None,
) -> dict[str, Any]:
    kwargs = {
        "Bucket": bucket_name,
        "Key": key,
        "Body": json.dumps(body, indent=2, sort_keys=True),
        "ContentType": "application/json",
    }
    if if_none_match is not None:
        kwargs["IfNoneMatch"] = if_none_match
    if if_match is not None:
        kwargs["IfMatch"] = if_match
    return s3_client.put_object(**kwargs)


def read_lock_object(
    s3_client: Any,
    bucket_name: str,
    key: str,
) -> tuple[dict[str, Any], str] | None:
    try:
        head = s3_client.head_object(Bucket=bucket_name, Key=key)
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
    except ClientError as exc:
        if is_not_found(exc):
            return None
        raise

    body = response["Body"]
    try:
        raw_body = body.read()
    finally:
        body.close()

    if isinstance(raw_body, bytes):
        raw_body = raw_body.decode("utf-8")

    return json.loads(raw_body), strip_etag(head["ETag"])


def can_reclaim(lock: dict[str, Any], now: datetime) -> bool:
    status = lock.get("status")
    if status == "failed":
        return True
    if status != "processing":
        return False

    expires_at = parse_timestamp(lock.get("processing_expires_at"))
    return expires_at is not None and expires_at < now


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def response_etag(response: dict[str, Any]) -> str | None:
    etag = response.get("ETag")
    return strip_etag(etag) if etag else None


def strip_etag(etag: str) -> str:
    return etag.strip('"')


def is_precondition_failed(exc: ClientError) -> bool:
    return error_code(exc) in {"PreconditionFailed", "412"}


def is_not_found(exc: ClientError) -> bool:
    return error_code(exc) in {"NoSuchKey", "NotFound", "404"}


def error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))
