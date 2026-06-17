from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable

try:
    from .cloudfront_logs import list_log_objects, parse_log_object
    from .config import LogProcessorConfig
    from .ledger import claim_log_object, mark_complete, mark_failed
    from .output_writer import write_records
except ImportError:
    from cloudfront_logs import list_log_objects, parse_log_object
    from config import LogProcessorConfig
    from ledger import claim_log_object, mark_complete, mark_failed
    from output_writer import write_records


def process_logs(
    config: LogProcessorConfig,
    s3_client: Any,
    dynamodb_client: Any,
    *,
    report_error: Callable[[str], None] = print,
) -> dict[str, Any]:
    log_objects = list_log_objects(s3_client, config.logs_bucket_name, config.logs_prefix)
    visitor_tracker: dict[str, set[str]] = defaultdict(set)
    claimed_files = 0
    processed_files = 0
    skipped_files = 0
    failed_files = 0
    output_keys: list[str] = []

    for log_object in log_objects:
        if config.max_files is not None and claimed_files >= config.max_files:
            break

        claimed_object_id = claim_log_object(
            dynamodb_client,
            config.processed_log_files_table,
            config.logs_bucket_name,
            log_object,
        )
        if claimed_object_id is None:
            skipped_files += 1
            continue

        claimed_files += 1

        try:
            records_by_date = parse_log_object(s3_client, config.logs_bucket_name, log_object.key)
            for date, records in records_by_date.items():
                visitor_tracker[date].update(record["viewer_ip"] for record in records)

            object_output_keys = write_records(
                s3_client,
                config.report_bucket_name,
                claimed_object_id,
                records_by_date,
            )
            record_count = sum(len(records) for records in records_by_date.values())
            mark_complete(
                dynamodb_client,
                config.processed_log_files_table,
                claimed_object_id,
                record_count,
                object_output_keys,
            )

            processed_files += 1
            output_keys.extend(object_output_keys)
        except Exception as exc:
            failed_files += 1
            mark_failed(
                dynamodb_client,
                config.processed_log_files_table,
                claimed_object_id,
                exc,
            )
            report_error(f"Failed processing s3://{config.logs_bucket_name}/{log_object.key}: {exc}")

    return build_summary(
        visitor_tracker,
        log_files_found=len(log_objects),
        log_files_limit=config.max_files,
        log_files_claimed=claimed_files,
        log_files_processed=processed_files,
        log_files_skipped=skipped_files,
        log_files_failed=failed_files,
        output_keys=output_keys,
    )


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
) -> dict[str, Any]:
    daily_counts = {date: len(visitors) for date, visitors in visitor_tracker.items()}
    sorted_dates = sorted(daily_counts.keys())
    total_visits = sum(daily_counts.values())

    return {
        "daily-visits": daily_counts[sorted_dates[-1]] if sorted_dates else 0,
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
    }
