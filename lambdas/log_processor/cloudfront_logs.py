from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import gzip
from io import TextIOWrapper
import re
from typing import Any
from urllib.parse import unquote


BOT_PATTERN = re.compile(
    r"bot|spider|crawl|slurp|fetch|python-requests|curl|wget|monitor",
    re.I,
)


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

            objects.append(
                LogObject(
                    key=key,
                    etag=obj["ETag"].strip('"'),
                    last_modified=obj["LastModified"].isoformat(),
                    size=obj["Size"],
                )
            )

    return sorted(objects, key=lambda item: item.key)


def parse_log_line(line: str, source_key: str) -> dict[str, Any] | None:
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
            for line in reader:
                record = parse_log_line(line, key)
                if record is None:
                    continue
                records_by_date[record["date"]].append(record)
    finally:
        body.close()

    return records_by_date
