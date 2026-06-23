from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any

from botocore.exceptions import ClientError

try:
    from .ledger import is_not_found
    from .output_writer import OUTPUT_PREFIX
except ImportError:
    from ledger import is_not_found
    from output_writer import OUTPUT_PREFIX


STATE_KEY = f"{OUTPUT_PREFIX}/state.json"


@dataclass(frozen=True)
class ProcessingState:
    source_cursor_key: str | None = None


def read_processing_state(s3_client: Any, bucket_name: str) -> ProcessingState:
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=STATE_KEY)
    except ClientError as exc:
        if is_not_found(exc):
            return ProcessingState()
        raise

    body = response["Body"]
    try:
        content = body.read()
    finally:
        close = getattr(body, "close", None)
        if close is not None:
            close()

    if isinstance(content, bytes):
        content = content.decode("utf-8")

    payload = json.loads(content)
    cursor = payload.get("source_cursor_key")
    return ProcessingState(source_cursor_key=cursor if isinstance(cursor, str) and cursor else None)


def write_processing_state(s3_client: Any, bucket_name: str, state: ProcessingState) -> None:
    payload = {
        "source_cursor_key": state.source_cursor_key,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    s3_client.put_object(
        Bucket=bucket_name,
        Key=STATE_KEY,
        Body=json.dumps(payload, indent=2, sort_keys=True),
        ContentType="application/json",
    )
