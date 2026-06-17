from __future__ import annotations

from typing import Any

try:
    from .config import LogProcessorConfig
except ImportError:
    from config import LogProcessorConfig


def create_s3_client() -> Any:
    import boto3

    return boto3.client("s3")


def create_dynamodb_client(config: LogProcessorConfig) -> Any:
    import boto3

    return boto3.client(
        "dynamodb",
        region_name=config.dynamodb_region,
        endpoint_url=config.dynamodb_endpoint,
        aws_access_key_id=config.dynamodb_access_key_id,
        aws_secret_access_key=config.dynamodb_secret_access_key,
    )
