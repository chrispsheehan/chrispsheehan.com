from __future__ import annotations

import json
from typing import Any


OUTPUT_PREFIX = "data/cost-explorer"
SUMMARY_KEY = f"{OUTPUT_PREFIX}/data.json"
HISTORY_PREFIX = f"{OUTPUT_PREFIX}/history/"


def history_key(billing_month: str) -> str:
    return f"{HISTORY_PREFIX}month={billing_month}/data.json"


def write_summary(s3_client: Any, bucket_name: str, summary: dict[str, Any]) -> None:
    s3_client.put_object(
        Bucket=bucket_name,
        Key=SUMMARY_KEY,
        Body=json.dumps(summary, indent=2),
        ContentType="application/json",
    )


def write_history(s3_client: Any, bucket_name: str, summary: dict[str, Any]) -> str:
    key = history_key(summary["billing-month"])
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(summary, indent=2),
        ContentType="application/json",
    )
    return key
