from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Callable

try:
    from .aggregate_state import AggregateState, update_aggregate_state
    from .cloudfront_logs import LogObject, list_log_objects, parse_log_object
    from .config import LogProcessorConfig
    from .ledger import claim_log_object, mark_complete, mark_failed
    from .output_writer import write_records
    from .state import ProcessingState, read_processing_state, write_processing_state
except ImportError:
    from aggregate_state import AggregateState, update_aggregate_state
    from cloudfront_logs import LogObject, list_log_objects, parse_log_object
    from config import LogProcessorConfig
    from ledger import claim_log_object, mark_complete, mark_failed
    from output_writer import write_records
    from state import ProcessingState, read_processing_state, write_processing_state

logger = logging.getLogger(__name__)
PUBLIC_DAILY_SERIES_DAYS = 30


def process_logs(
    config: LogProcessorConfig,
    s3_client: Any,
    *,
    log_objects: list[LogObject] | None = None,
    use_cursor: bool = True,
    report_error: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    logger.info(
        "Listing CloudFront log objects bucket=%s prefix=%s",
        config.logs_bucket_name,
        config.logs_prefix,
    )
    processing_state = (
        read_processing_state(s3_client, config.database_bucket_name)
        if log_objects is None and use_cursor
        else ProcessingState()
    )
    apply_max_files = log_objects is None
    effective_max_files = config.max_files if apply_max_files else None
    if log_objects is None:
        logger.info(
            "Loaded log processor state database_bucket=%s source_cursor_key=%s use_cursor=%s",
            config.database_bucket_name,
            processing_state.source_cursor_key,
            use_cursor,
        )
        log_objects = list_log_objects(
            s3_client,
            config.logs_bucket_name,
            config.logs_prefix,
            start_after=processing_state.source_cursor_key if use_cursor else None,
            modified_since=None if use_cursor else datetime.now(timezone.utc) - timedelta(hours=48),
        )
    else:
        log_objects = sorted(log_objects, key=lambda item: item.key)
    claimed_files = 0
    processed_files = 0
    skipped_files = 0
    failed_files = 0
    run_output_keys: list[str] = []
    cursor_outcomes: list[tuple[str, bool]] = []
    staged_files: list[
        tuple[LogObject, Any, dict[str, list[dict[str, Any]]], list[str], int]
    ] = []
    new_records_by_date: dict[str, list[dict[str, Any]]] = {}
    failed_source_keys: list[str] = []

    logger.info(
        "Found %s CloudFront log object(s) max_claimed_files=%s",
        len(log_objects),
        effective_max_files,
    )

    for index, log_object in enumerate(log_objects, start=1):
        if effective_max_files is not None and claimed_files >= effective_max_files:
            logger.info(
                "Reached max claimed file limit limit=%s claimed=%s remaining=%s",
                effective_max_files,
                claimed_files,
                len(log_objects) - index + 1,
            )
            break

        logger.info(
            "Checking log file %s/%s key=%s size=%s etag=%s",
            index,
            len(log_objects),
            log_object.key,
            log_object.size,
            log_object.etag,
        )
        decision = claim_log_object(
            s3_client,
            config.database_bucket_name,
            config.logs_bucket_name,
            log_object,
        )
        if decision.status == "complete":
            skipped_files += 1
            logger.info(
                "Skipping already completed log file %s/%s key=%s skipped=%s",
                index,
                len(log_objects),
                log_object.key,
                skipped_files,
            )
            cursor_outcomes.append((log_object.key, True))
            continue

        if decision.status == "busy":
            skipped_files += 1
            cursor_outcomes.append((log_object.key, False))
            logger.info(
                "Skipping busy log file %s/%s key=%s skipped=%s",
                index,
                len(log_objects),
                log_object.key,
                skipped_files,
            )
            continue

        claim = decision.claim
        assert claim is not None
        claimed_files += 1
        logger.info(
            "Processing claimed log file %s/%s key=%s claimed=%s",
            index,
            len(log_objects),
            log_object.key,
            claimed_files,
        )

        try:
            records_by_date = parse_log_object(s3_client, config.logs_bucket_name, log_object.key)
            for date, records in records_by_date.items():
                logger.debug(
                    "Parsed records for log file key=%s date=%s records=%s",
                    log_object.key,
                    date,
                    len(records),
                )

            object_output_keys = write_records(
                s3_client,
                config.database_bucket_name,
                claim.object_id,
                records_by_date,
            )
            record_count = sum(len(records) for records in records_by_date.values())
            staged_files.append(
                (log_object, claim, records_by_date, object_output_keys, record_count)
            )
            for date, records in records_by_date.items():
                new_records_by_date.setdefault(date, []).extend(records)
        except Exception as exc:
            failed_files += 1
            cursor_outcomes.append((log_object.key, False))
            failed_source_keys.append(log_object.key)
            mark_failed(
                s3_client,
                config.database_bucket_name,
                claim,
                exc,
            )
            message = f"Failed processing s3://{config.logs_bucket_name}/{log_object.key}: {exc}"
            logger.exception(message)
            if report_error is not None:
                report_error(message)

    aggregate_state = update_aggregate_state(
        s3_client,
        config.database_bucket_name,
        new_records_by_date,
    )

    for log_object, claim, _records_by_date, object_output_keys, record_count in staged_files:
        mark_complete(
            s3_client,
            config.database_bucket_name,
            claim,
            record_count,
            object_output_keys,
        )
        cursor_outcomes.append((log_object.key, True))
        processed_files += 1
        run_output_keys.extend(object_output_keys)
        logger.info(
            "Completed log file key=%s records=%s output_keys=%s processed=%s failed=%s skipped=%s",
            log_object.key,
            record_count,
            len(object_output_keys),
            processed_files,
            failed_files,
            skipped_files,
        )

    source_cursor_key = processing_state.source_cursor_key
    if use_cursor:
        outcomes_by_key = dict(cursor_outcomes)
        for log_object in log_objects:
            if log_object.key not in outcomes_by_key:
                break
            if not outcomes_by_key[log_object.key]:
                break
            source_cursor_key = log_object.key

    if use_cursor and source_cursor_key != processing_state.source_cursor_key:
        write_processing_state(
            s3_client,
            config.database_bucket_name,
            ProcessingState(source_cursor_key=source_cursor_key),
        )
        logger.info(
            "Updated log processor state database_bucket=%s source_cursor_key=%s",
            config.database_bucket_name,
            source_cursor_key,
        )

    summary = build_summary_from_aggregate_state(
        aggregate_state,
        log_files_found=len(log_objects),
        log_files_limit=effective_max_files,
        log_files_claimed=claimed_files,
        log_files_processed=processed_files,
        log_files_skipped=skipped_files,
        log_files_failed=failed_files,
        output_keys=[],
        run_output_keys=run_output_keys,
        failed_source_keys=failed_source_keys,
    )
    logger.info(
        "Finished log processor run found=%s claimed=%s processed=%s skipped=%s failed=%s run_output_keys=%s database_output_keys=%s total_visits=%s daily_visits=%s last_date=%s",
        summary["log-files-found"],
        summary["log-files-claimed"],
        summary["log-files-processed"],
        summary["log-files-skipped"],
        summary["log-files-failed"],
        len(summary["run-output-keys"]),
        len(summary["output-keys"]),
        summary["total-visits"],
        summary["daily-visits"],
        summary["last-date"],
    )
    return summary


def build_summary_from_aggregate_state(
    state: AggregateState,
    *,
    log_files_found: int,
    log_files_limit: int | None,
    log_files_claimed: int,
    log_files_processed: int,
    log_files_skipped: int,
    log_files_failed: int,
    output_keys: list[str],
    run_output_keys: list[str],
    failed_source_keys: list[str],
) -> dict[str, Any]:
    daily_counts = state.daily_visits
    sorted_dates = sorted(daily_counts)
    return {
        "daily-visits": daily_counts[sorted_dates[-1]] if sorted_dates else 0,
        "daily-visitor-counts": build_daily_visitor_counts(daily_counts),
        "total-visits": sum(daily_counts.values()),
        "range": len(sorted_dates),
        "last-date": sorted_dates[-1] if sorted_dates else None,
        "generated-at": datetime.now(timezone.utc).date().isoformat(),
        "log-files-found": log_files_found,
        "log-files-limit": log_files_limit,
        "log-files-claimed": log_files_claimed,
        "log-files-processed": log_files_processed,
        "log-files-skipped": log_files_skipped,
        "log-files-failed": log_files_failed,
        "output-keys": output_keys,
        "run-output-keys": run_output_keys,
        "failed-source-keys": failed_source_keys,
    }


def build_summary(
    visitor_tracker: dict[str, set[str]],
    *,
    log_files_found: int,
    log_files_limit: int | None,
    log_files_claimed: int,
    log_files_processed: int,
    log_files_skipped: int,
    log_files_failed: int,
    output_keys: list[str],
    run_output_keys: list[str],
) -> dict[str, Any]:
    daily_counts = {date: len(visitors) for date, visitors in visitor_tracker.items()}
    sorted_dates = sorted(daily_counts.keys())
    total_visits = sum(daily_counts.values())

    return {
        "daily-visits": daily_counts[sorted_dates[-1]] if sorted_dates else 0,
        "daily-visitor-counts": build_daily_visitor_counts(daily_counts),
        "total-visits": total_visits,
        "range": len(sorted_dates),
        "last-date": sorted_dates[-1] if sorted_dates else None,
        "generated-at": datetime.now(timezone.utc).date().isoformat(),
        "log-files-found": log_files_found,
        "log-files-limit": log_files_limit,
        "log-files-claimed": log_files_claimed,
        "log-files-processed": log_files_processed,
        "log-files-skipped": log_files_skipped,
        "log-files-failed": log_files_failed,
        "output-keys": output_keys,
        "run-output-keys": run_output_keys,
    }


def build_daily_visitor_counts(daily_counts: dict[str, int]) -> list[dict[str, Any]]:
    if not daily_counts:
        return []

    last_day = datetime.strptime(max(daily_counts), "%Y-%m-%d").date()
    first_day = last_day - timedelta(days=PUBLIC_DAILY_SERIES_DAYS - 1)
    return [
        {
            "date": (first_day + timedelta(days=offset)).isoformat(),
            "visitors": daily_counts.get(
                (first_day + timedelta(days=offset)).isoformat(),
                0,
            ),
        }
        for offset in range(PUBLIC_DAILY_SERIES_DAYS)
    ]
