from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

try:
    from .cloudfront_logs import LogObject
except ImportError:
    from cloudfront_logs import LogObject


PROCESSING_LEASE_SECONDS = 15 * 60


def utc_timestamp(moment: datetime | None = None) -> str:
    return (moment or datetime.now(timezone.utc)).isoformat()


def object_id(bucket_name: str, key: str, etag: str) -> str:
    source = f"{bucket_name}\0{key}\0{etag}"
    return sha256(source.encode("utf-8")).hexdigest()


def claim_log_object(
    dynamodb_client: Any,
    table_name: str,
    bucket_name: str,
    log_object: LogObject,
) -> str | None:
    claimed_object_id = object_id(bucket_name, log_object.key, log_object.etag)
    claimed_at = datetime.now(timezone.utc)

    try:
        dynamodb_client.put_item(
            TableName=table_name,
            Item={
                "object_id": {"S": claimed_object_id},
                "source_bucket": {"S": bucket_name},
                "source_key": {"S": log_object.key},
                "source_etag": {"S": log_object.etag},
                "source_last_modified": {"S": log_object.last_modified},
                "source_size": {"N": str(log_object.size)},
                "status": {"S": "processing"},
                "claimed_at": {"S": utc_timestamp(claimed_at)},
                "processing_expires_at": {
                    "S": utc_timestamp(
                        claimed_at + timedelta(seconds=PROCESSING_LEASE_SECONDS)
                    )
                },
            },
            ConditionExpression=(
                "attribute_not_exists(object_id) OR "
                "#status = :failed OR "
                "(#status = :processing AND processing_expires_at < :now)"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":failed": {"S": "failed"},
                ":processing": {"S": "processing"},
                ":now": {"S": utc_timestamp(claimed_at)},
            },
        )
    except dynamodb_client.exceptions.ConditionalCheckFailedException:
        return None

    return claimed_object_id


def mark_complete(
    dynamodb_client: Any,
    table_name: str,
    claimed_object_id: str,
    record_count: int,
    output_keys: list[str],
) -> None:
    dynamodb_client.update_item(
        TableName=table_name,
        Key={"object_id": {"S": claimed_object_id}},
        UpdateExpression=(
            "SET #status = :status, processed_at = :processed_at, "
            "record_count = :record_count, output_keys = :output_keys "
            "REMOVE #error, processing_expires_at"
        ),
        ExpressionAttributeNames={"#status": "status", "#error": "error"},
        ExpressionAttributeValues={
            ":status": {"S": "complete"},
            ":processed_at": {"S": utc_timestamp()},
            ":record_count": {"N": str(record_count)},
            ":output_keys": {"L": [{"S": key} for key in output_keys]},
        },
    )


def mark_failed(
    dynamodb_client: Any,
    table_name: str,
    claimed_object_id: str,
    exc: Exception,
) -> None:
    dynamodb_client.update_item(
        TableName=table_name,
        Key={"object_id": {"S": claimed_object_id}},
        UpdateExpression=(
            "SET #status = :status, failed_at = :failed_at, error = :error "
            "REMOVE processing_expires_at"
        ),
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": {"S": "failed"},
            ":failed_at": {"S": utc_timestamp()},
            ":error": {"S": str(exc)[:1000]},
        },
    )
