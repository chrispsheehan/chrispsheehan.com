from __future__ import annotations

from collections import defaultdict
import json
import logging
from typing import Any

try:
    from .output_writer import REQUESTS_PREFIX
except ImportError:
    from output_writer import REQUESTS_PREFIX

logger = logging.getLogger(__name__)


def build_visitor_tracker_from_database(
    s3_client: Any,
    bucket_name: str,
) -> tuple[dict[str, set[str]], list[str]]:
    visitor_tracker: dict[str, set[str]] = defaultdict(set)
    output_keys = list_request_record_keys(s3_client, bucket_name)

    for key in output_keys:
        for record in read_request_records(s3_client, bucket_name, key):
            date = record.get("date")
            viewer_ip = record.get("viewer_ip")
            if not date or not viewer_ip:
                logger.warning("Skipping request record missing date or viewer_ip key=%s", key)
                continue
            visitor_tracker[date].add(viewer_ip)

    return visitor_tracker, output_keys


def list_request_record_keys(s3_client: Any, bucket_name: str) -> list[str]:
    paginator = s3_client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=REQUESTS_PREFIX)
    keys: list[str] = []

    for page in page_iterator:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".jsonl"):
                keys.append(key)

    return sorted(keys)


def read_request_records(s3_client: Any, bucket_name: str, key: str) -> list[dict[str, Any]]:
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    body = response["Body"]

    try:
        content = body.read()
    finally:
        close = getattr(body, "close", None)
        if close is not None:
            close()

    if isinstance(content, bytes):
        text = content.decode("utf-8")
    else:
        text = str(content)

    records = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Skipping malformed request record key=%s line=%s", key, line_number)

    return records
