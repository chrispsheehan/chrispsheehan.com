from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import gzip
from io import TextIOWrapper
import re
from typing import Any
from urllib.parse import unquote


BOT_PATTERN = re.compile(
    r"bot|spider|crawl|slurp|fetch|python-requests|curl|wget|monitor",
    re.I,
)

LEGACY_LOG_FIELDS = [
    "date",
    "time",
    "x-edge-location",
    "sc-bytes",
    "c-ip",
    "cs-method",
    "cs(Host)",
    "cs-uri-stem",
    "sc-status",
    "cs(Referer)",
    "cs(User-Agent)",
    "cs-uri-query",
    "cs(Cookie)",
    "x-edge-result-type",
    "x-edge-request-id",
]


@dataclass(frozen=True)
class LogObject:
    key: str
    etag: str
    last_modified: str
    size: int


def list_log_objects(
    s3_client: Any,
    bucket_name: str,
    prefix: str,
    *,
    start_after: str | None = None,
    modified_since: datetime | None = None,
) -> list[LogObject]:
    paginator = s3_client.get_paginator("list_objects_v2")
    paginate_kwargs = {
        "Bucket": bucket_name,
        "Prefix": prefix,
    }
    if start_after:
        paginate_kwargs["StartAfter"] = start_after
    page_iterator = paginator.paginate(**paginate_kwargs)
    objects = []

    for page in page_iterator:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".gz"):
                continue
            if modified_since is not None and obj["LastModified"] < modified_since:
                continue

            objects.append(
                LogObject(
                    key=key,
                    etag=obj["ETag"].strip('"'),
                    last_modified=obj["LastModified"].isoformat(),
                    size=obj["Size"],
                )
            )

    return sorted(objects, key=lambda item: item.key)


def parse_log_line(
    line: str,
    source_key: str,
    fields: list[str] | None = None,
) -> dict[str, Any] | None:
    if line.startswith("#"):
        return None

    parts = line.rstrip("\n").split("\t")
    fields = fields or LEGACY_LOG_FIELDS
    if len(parts) < len(fields):
        return None

    values = dict(zip(fields, parts, strict=False))
    user_agent = unquote(values.get("cs(User-Agent)", ""))
    if BOT_PATTERN.search(user_agent):
        return None

    required_fields = [
        "date",
        "time",
        "x-edge-location",
        "c-ip",
        "cs-method",
        "cs(Host)",
        "cs-uri-stem",
        "sc-status",
        "x-edge-result-type",
        "x-edge-request-id",
    ]
    if any(field not in values for field in required_fields):
        return None

    bytes_sent = values.get("sc-bytes", "")
    status = values["sc-status"]
    referer = values.get("cs(Referer)", "-")
    query = values.get("cs-uri-query", "-")
    country = values.get("c-country", "").upper()
    record = {
        "date": values["date"],
        "time": values["time"],
        "edge_location": values["x-edge-location"],
        "bytes_sent": int(bytes_sent) if bytes_sent.isdigit() else None,
        "viewer_ip": values["c-ip"],
        "method": values["cs-method"],
        "host": values["cs(Host)"],
        "uri": unquote(values["cs-uri-stem"]),
        "status": int(status) if status.isdigit() else None,
        "referer": unquote(referer) if referer != "-" else None,
        "user_agent": user_agent,
        "query": unquote(query) if query != "-" else None,
        "edge_result_type": values["x-edge-result-type"],
        "request_id": values["x-edge-request-id"],
        "source_key": source_key,
    }
    if len(country) == 2 and country.isalpha():
        record["country"] = country
    return record


def parse_log_object(
    s3_client: Any,
    bucket_name: str,
    key: str,
) -> dict[str, list[dict[str, Any]]]:
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    records_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    body = response["Body"]

    try:
        with gzip.GzipFile(fileobj=body) as gzip_body:
            reader = TextIOWrapper(gzip_body, encoding="utf-8", errors="replace")
            fields = None
            for line in reader:
                if line.startswith("#Fields:"):
                    fields = line.removeprefix("#Fields:").strip().split()
                    continue
                record = parse_log_line(line, key, fields)
                if record is None:
                    continue
                records_by_date[record["date"]].append(record)
    finally:
        body.close()

    return records_by_date


def log_object_from_s3_record(record: dict[str, Any]) -> tuple[str, LogObject]:
    bucket_name = record["s3"]["bucket"]["name"]
    object_data = record["s3"]["object"]
    return bucket_name, LogObject(
        key=unquote(object_data["key"].replace("+", " ")),
        etag=object_data["eTag"],
        last_modified=record.get("eventTime", ""),
        size=int(object_data.get("size", 0)),
    )
