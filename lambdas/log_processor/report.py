from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import logging
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

logger = logging.getLogger(__name__)


def process_logs(
    config: LogProcessorConfig,
    s3_client: Any,
    dynamodb_client: Any,
    *,
    report_error: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    logger.info(
        "Listing CloudFront log objects bucket=%s prefix=%s",
        config.logs_bucket_name,
        config.logs_prefix,
    )
    log_objects = list_log_objects(s3_client, config.logs_bucket_name, config.logs_prefix)
    visitor_tracker: dict[str, set[str]] = defaultdict(set)
    claimed_files = 0
    processed_files = 0
    skipped_files = 0
    failed_files = 0
    output_keys: list[str] = []

    logger.info(
        "Found %s CloudFront log object(s) max_claimed_files=%s",
        len(log_objects),
        config.max_files,
    )

    for index, log_object in enumerate(log_objects, start=1):
        if config.max_files is not None and claimed_files >= config.max_files:
            logger.info(
                "Reached max claimed file limit limit=%s claimed=%s remaining=%s",
                config.max_files,
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
        claimed_object_id = claim_log_object(
            dynamodb_client,
            config.processed_log_files_table,
            config.logs_bucket_name,
            log_object,
        )
        if claimed_object_id is None:
            skipped_files += 1
            logger.info(
                "Skipping already completed log file %s/%s key=%s skipped=%s",
                index,
                len(log_objects),
                log_object.key,
                skipped_files,
            )
            continue

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
                visitor_tracker[date].update(record["viewer_ip"] for record in records)
                logger.debug(
                    "Parsed records for log file key=%s date=%s records=%s unique_viewers_for_date=%s",
                    log_object.key,
                    date,
                    len(records),
                    len(visitor_tracker[date]),
                )

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
            logger.info(
                "Completed log file %s/%s key=%s records=%s output_keys=%s processed=%s failed=%s skipped=%s",
                index,
                len(log_objects),
                log_object.key,
                record_count,
                len(object_output_keys),
                processed_files,
                failed_files,
                skipped_files,
            )
        except Exception as exc:
            failed_files += 1
            mark_failed(
                dynamodb_client,
                config.processed_log_files_table,
                claimed_object_id,
                exc,
            )
            message = f"Failed processing s3://{config.logs_bucket_name}/{log_object.key}: {exc}"
            logger.exception(message)
            if report_error is not None:
                report_error(message)

    summary = build_summary(
        visitor_tracker,
        log_files_found=len(log_objects),
        log_files_limit=config.max_files,
        log_files_claimed=claimed_files,
        log_files_processed=processed_files,
        log_files_skipped=skipped_files,
        log_files_failed=failed_files,
        output_keys=output_keys,
    )
    logger.info(
        "Finished log processor run found=%s claimed=%s processed=%s skipped=%s failed=%s output_keys=%s total_visits=%s daily_visits=%s last_date=%s",
        summary["log-files-found"],
        summary["log-files-claimed"],
        summary["log-files-processed"],
        summary["log-files-skipped"],
        summary["log-files-failed"],
        len(summary["output-keys"]),
        summary["total-visits"],
        summary["daily-visits"],
        summary["last-date"],
    )
    return summary


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
