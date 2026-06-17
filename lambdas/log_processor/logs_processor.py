from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import gzip
from hashlib import sha256
from io import TextIOWrapper
import json
import os
import re
from typing import Any
from urllib.parse import unquote

import boto3

s3 = boto3.client("s3")
dynamodb = boto3.client("dynamodb")

BOT_PATTERN = re.compile(
    r"bot|spider|crawl|slurp|fetch|python-requests|curl|wget|monitor",
    re.I,
)

OUTPUT_PREFIX = "data/log-processor"


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} must be set")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _object_id(bucket_name: str, key: str, etag: str) -> str:
    source = f"{bucket_name}\0{key}\0{etag}"
    return sha256(source.encode("utf-8")).hexdigest()


def _list_log_objects(bucket_name: str, prefix: str) -> list[dict[str, Any]]:
    paginator = s3.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    objects = []

    for page in page_iterator:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".gz"):
                continue

            objects.append(
                {
                    "key": key,
                    "etag": obj["ETag"].strip('"'),
                    "last_modified": obj["LastModified"].isoformat(),
                    "size": obj["Size"],
                }
            )

    return sorted(objects, key=lambda item: (item["last_modified"], item["key"]))


def _claim_log_object(table_name: str, bucket_name: str, log_object: dict[str, Any]) -> str | None:
    object_id = _object_id(bucket_name, log_object["key"], log_object["etag"])

    try:
        dynamodb.put_item(
            TableName=table_name,
            Item={
                "object_id": {"S": object_id},
                "source_bucket": {"S": bucket_name},
                "source_key": {"S": log_object["key"]},
                "source_etag": {"S": log_object["etag"]},
                "source_last_modified": {"S": log_object["last_modified"]},
                "source_size": {"N": str(log_object["size"])},
                "status": {"S": "processing"},
                "claimed_at": {"S": _now()},
            },
            ConditionExpression="attribute_not_exists(object_id) OR #status <> :complete",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":complete": {"S": "complete"}},
        )
    except dynamodb.exceptions.ConditionalCheckFailedException:
        return None

    return object_id


def _mark_complete(
    table_name: str,
    object_id: str,
    record_count: int,
    output_keys: list[str],
) -> None:
    dynamodb.update_item(
        TableName=table_name,
        Key={"object_id": {"S": object_id}},
        UpdateExpression=(
            "SET #status = :status, processed_at = :processed_at, "
            "record_count = :record_count, output_keys = :output_keys "
            "REMOVE #error"
        ),
        ExpressionAttributeNames={"#status": "status", "#error": "error"},
        ExpressionAttributeValues={
            ":status": {"S": "complete"},
            ":processed_at": {"S": _now()},
            ":record_count": {"N": str(record_count)},
            ":output_keys": {"L": [{"S": key} for key in output_keys]},
        },
    )


def _mark_failed(table_name: str, object_id: str, exc: Exception) -> None:
    dynamodb.update_item(
        TableName=table_name,
        Key={"object_id": {"S": object_id}},
        UpdateExpression="SET #status = :status, failed_at = :failed_at, error = :error",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": {"S": "failed"},
            ":failed_at": {"S": _now()},
            ":error": {"S": str(exc)[:1000]},
        },
    )


def _parse_log_line(line: str, source_key: str) -> dict[str, Any] | None:
    if line.startswith("#"):
        return None

    parts = line.rstrip("\n").split("\t")
    if len(parts) < 15:
        return None

    user_agent = unquote(parts[10])
    if BOT_PATTERN.search(user_agent):
        return None

    return {
        "date": parts[0],
        "time": parts[1],
        "edge_location": parts[2],
        "bytes_sent": int(parts[3]) if parts[3].isdigit() else None,
        "viewer_ip": parts[4],
        "method": parts[5],
        "host": parts[6],
        "uri": unquote(parts[7]),
        "status": int(parts[8]) if parts[8].isdigit() else None,
        "referer": unquote(parts[9]) if parts[9] != "-" else None,
        "user_agent": user_agent,
        "query": unquote(parts[11]) if parts[11] != "-" else None,
        "edge_result_type": parts[13],
        "request_id": parts[14],
        "source_key": source_key,
    }


def _parse_log_object(bucket_name: str, key: str) -> dict[str, list[dict[str, Any]]]:
    response = s3.get_object(Bucket=bucket_name, Key=key)
    records_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    body = response["Body"]

    try:
        with gzip.GzipFile(fileobj=body) as gzip_body:
            reader = TextIOWrapper(gzip_body, encoding="utf-8", errors="replace")
            for line in reader:
                record = _parse_log_line(line, key)
                if record is None:
                    continue
                records_by_date[record["date"]].append(record)
    finally:
        body.close()

    return records_by_date


def _write_records(
    bucket_name: str,
    object_id: str,
    records_by_date: dict[str, list[dict[str, Any]]],
) -> list[str]:
    output_keys = []
    source_hash = object_id[:24]

    for date, records in sorted(records_by_date.items()):
        if not records:
            continue

        key = f"{OUTPUT_PREFIX}/requests/date={date}/{source_hash}.jsonl"
        body = "\n".join(json.dumps(record, separators=(",", ":")) for record in records)
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=f"{body}\n",
            ContentType="application/x-ndjson",
        )
        output_keys.append(key)

    return output_keys


def logs_report(report_bucket_name: str) -> dict[str, Any]:
    logs_bucket_name = _required_env("S3_LOGS_BUCKET")
    table_name = _required_env("PROCESSED_LOG_FILES_TABLE")
    logs_prefix = os.environ.get("S3_LOGS_PREFIX", "")

    log_objects = _list_log_objects(logs_bucket_name, logs_prefix)
    visitor_tracker: dict[str, set[str]] = defaultdict(set)
    processed_files = 0
    skipped_files = 0
    failed_files = 0
    output_keys: list[str] = []

    for log_object in log_objects:
        object_id = _claim_log_object(table_name, logs_bucket_name, log_object)
        if object_id is None:
            skipped_files += 1
            continue

        try:
            records_by_date = _parse_log_object(logs_bucket_name, log_object["key"])
            for date, records in records_by_date.items():
                visitor_tracker[date].update(record["viewer_ip"] for record in records)

            object_output_keys = _write_records(report_bucket_name, object_id, records_by_date)
            record_count = sum(len(records) for records in records_by_date.values())
            _mark_complete(table_name, object_id, record_count, object_output_keys)

            processed_files += 1
            output_keys.extend(object_output_keys)
        except Exception as exc:
            failed_files += 1
            _mark_failed(table_name, object_id, exc)
            print(f"Failed processing s3://{logs_bucket_name}/{log_object['key']}: {exc}")

    daily_counts = {date: len(visitors) for date, visitors in visitor_tracker.items()}
    sorted_dates = sorted(daily_counts.keys())
    total_visits = sum(daily_counts.values())

    return {
        "daily-visits": daily_counts[sorted_dates[-1]] if sorted_dates else 0,
        "total-visits": total_visits,
        "range": len(sorted_dates),
        "last-date": sorted_dates[-1] if sorted_dates else None,
        "generated-at": datetime.now(timezone.utc).date().isoformat(),
        "log-files-found": len(log_objects),
        "log-files-processed": processed_files,
        "log-files-skipped": skipped_files,
        "log-files-failed": failed_files,
        "output-keys": output_keys,
    }
