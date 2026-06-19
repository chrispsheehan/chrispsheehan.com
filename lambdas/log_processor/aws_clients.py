from __future__ import annotations

from typing import Any


def create_s3_client() -> Any:
    import boto3

    return boto3.client("s3")
