import json
import logging
import sys
from typing import Any

try:
    from .aws_clients import create_s3_client
    from .cloudfront_logs import LogObject, log_object_from_s3_record
    from .config import load_config
    from .logging_config import configure_logging
    from .logs_processor import logs_report
    from .output_writer import SUMMARY_KEY, write_summary
except ImportError:
    from aws_clients import create_s3_client
    from cloudfront_logs import LogObject, log_object_from_s3_record
    from config import load_config
    from logging_config import configure_logging
    from logs_processor import logs_report
    from output_writer import SUMMARY_KEY, write_summary

logger = logging.getLogger(__name__)


def handle_event(event, context, *, s3_client=None, env=None):
    config = load_config(env=env)
    configure_logging(config.log_level)

    request_id = getattr(context, "aws_request_id", None)
    logger.info(
        "Starting log processor invocation request_id=%s logs_bucket=%s logs_prefix=%s report_bucket=%s database_bucket=%s max_files=%s",
        request_id,
        config.logs_bucket_name,
        config.logs_prefix,
        config.report_bucket_name,
        config.database_bucket_name,
        config.max_files,
    )

    s3_client = s3_client or create_s3_client()

    if is_sqs_event(event):
        return handle_sqs_event(event, config, s3_client)

    combined = logs_report(
        config.database_bucket_name,
        config=config,
        s3_client=s3_client,
        use_cursor=not bool(event.get("reconcile")),
    )

    write_summary(s3_client, config.report_bucket_name, combined)
    s3_path = f"s3://{config.report_bucket_name}/{SUMMARY_KEY}"

    logger.info("Log processor summary written s3_path=%s", s3_path)
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "s3_path": s3_path,
                "log-files-found": combined["log-files-found"],
                "log-files-claimed": combined["log-files-claimed"],
                "log-files-processed": combined["log-files-processed"],
                "log-files-skipped": combined["log-files-skipped"],
                "log-files-failed": combined["log-files-failed"],
            }
        ),
    }


def is_sqs_event(event: Any) -> bool:
    records = event.get("Records") if isinstance(event, dict) else None
    return bool(records) and all(record.get("eventSource") == "aws:sqs" for record in records)


def handle_sqs_event(event, config, s3_client):
    log_objects_by_identity: dict[tuple[str, str], LogObject] = {}
    message_ids_by_identity: dict[tuple[str, str], set[str]] = {}
    failed_message_ids: set[str] = set()

    for message in event["Records"]:
        message_id = message["messageId"]
        try:
            payload = json.loads(message["body"])
            for s3_record in payload.get("Records", []):
                bucket_name, log_object = log_object_from_s3_record(s3_record)
                if bucket_name != config.logs_bucket_name:
                    raise ValueError(f"Unexpected S3 event bucket: {bucket_name}")
                if not log_object.key.startswith(config.logs_prefix) or not log_object.key.endswith(
                    ".gz"
                ):
                    continue
                identity = (log_object.key, log_object.etag)
                log_objects_by_identity[identity] = log_object
                message_ids_by_identity.setdefault(identity, set()).add(message_id)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            logger.exception("Invalid SQS log notification message_id=%s", message_id)
            failed_message_ids.add(message_id)

    if not log_objects_by_identity:
        return {
            "batchItemFailures": [
                {"itemIdentifier": message_id}
                for message_id in sorted(failed_message_ids)
            ]
        }

    combined = logs_report(
        config.database_bucket_name,
        config=config,
        s3_client=s3_client,
        log_objects=list(log_objects_by_identity.values()),
        use_cursor=False,
    )
    if combined["log-files-processed"] or combined["log-files-failed"]:
        write_summary(s3_client, config.report_bucket_name, combined)

    failed_keys = set(combined["failed-source-keys"])
    failed_message_ids.update(
        {
            message_id
            for (key, _etag), message_ids in message_ids_by_identity.items()
            if key in failed_keys
            for message_id in message_ids
        }
    )
    return {
        "batchItemFailures": [
            {"itemIdentifier": message_id}
            for message_id in sorted(failed_message_ids)
        ]
    }


def lambda_handler(event, context):
    try:
        return handle_event(event, context)
    except Exception as exc:
        error_msg = f"Logs processor Lambda failed: {exc}"
        logger.exception(error_msg)

        if is_sqs_event(event):
            raise

        # Return 500 JSON for API Gateway / test invocations
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}


if __name__ == "__main__":
    result = lambda_handler({}, None)
    if result.get("statusCode") != 200:
        sys.exit(1)
