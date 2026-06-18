from __future__ import annotations

import json
from typing import Any


OUTPUT_PREFIX = "data/log-processor"
REQUESTS_PREFIX = f"{OUTPUT_PREFIX}/requests/"
SUMMARY_KEY = f"{OUTPUT_PREFIX}/data.json"
SUMMARY_METADATA_KEYS = {"output-keys", "run-output-keys"}


def write_records(
    s3_client: Any,
    bucket_name: str,
    object_id: str,
    records_by_date: dict[str, list[dict[str, Any]]],
) -> list[str]:
    output_keys = []
    source_hash = object_id[:24]

    for date, records in sorted(records_by_date.items()):
        if not records:
            continue

        key = f"{REQUESTS_PREFIX}date={date}/{source_hash}.jsonl"
        body = "\n".join(json.dumps(record, separators=(",", ":")) for record in records)
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=f"{body}\n",
            ContentType="application/x-ndjson",
        )
        output_keys.append(key)

    return output_keys


def write_summary(s3_client: Any, bucket_name: str, summary: dict[str, Any]) -> None:
    s3_client.put_object(
        Bucket=bucket_name,
        Key=SUMMARY_KEY,
        Body=json.dumps(public_summary(summary), indent=2),
        ContentType="application/json",
    )


def public_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if key not in SUMMARY_METADATA_KEYS}
