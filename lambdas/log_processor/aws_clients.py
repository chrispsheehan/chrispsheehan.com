from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

try:
    from .config import LogProcessorConfig
except ImportError:
    from config import LogProcessorConfig


def create_s3_client() -> Any:
    import boto3

    return boto3.client("s3")


def create_dynamodb_client(config: LogProcessorConfig) -> Any:
    import boto3

    return boto3.client("dynamodb", **dynamodb_client_kwargs(config))


def dynamodb_client_kwargs(config: LogProcessorConfig) -> dict[str, str]:
    kwargs = {
        "region_name": config.dynamodb_region,
        "endpoint_url": config.dynamodb_endpoint,
    }

    if config.dynamodb_access_key_id and config.dynamodb_secret_access_key:
        kwargs["aws_access_key_id"] = config.dynamodb_access_key_id
        kwargs["aws_secret_access_key"] = config.dynamodb_secret_access_key
    elif is_local_endpoint(config.dynamodb_endpoint):
        kwargs["aws_access_key_id"] = "DUMMYIDEXAMPLE"
        kwargs["aws_secret_access_key"] = "DUMMYEXAMPLEKEY"

    return kwargs


def is_local_endpoint(endpoint_url: str) -> bool:
    hostname = urlparse(endpoint_url).hostname
    return hostname in {"localhost", "127.0.0.1", "0.0.0.0", "dynamodb-local"}
