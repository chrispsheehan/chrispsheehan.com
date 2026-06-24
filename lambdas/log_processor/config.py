from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping

VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}


@dataclass(frozen=True)
class LogProcessorConfig:
    report_bucket_name: str
    database_bucket_name: str
    logs_bucket_name: str
    logs_prefix: str
    max_files: int | None
    log_level: str


def load_config(
    *,
    report_bucket_name: str | None = None,
    database_bucket_name: str | None = None,
    env: Mapping[str, str] | None = None,
) -> LogProcessorConfig:
    env = env or os.environ

    return LogProcessorConfig(
        report_bucket_name=report_bucket_name or required_env(env, "REPORT_BUCKET"),
        database_bucket_name=database_bucket_name or required_env(env, "DATABASE_BUCKET"),
        logs_bucket_name=required_env(env, "S3_LOGS_BUCKET"),
        logs_prefix=env.get("S3_LOGS_PREFIX", ""),
        max_files=optional_positive_int_env(env, "S3_LOGS_MAX_FILES"),
        log_level=log_level_env(env, "LOG_LEVEL"),
    )


def required_env(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if not value:
        raise ValueError(f"{name} must be set")
    return value


def optional_positive_int_env(env: Mapping[str, str], name: str) -> int | None:
    value = env.get(name)
    if value is None or value == "":
        return None

    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc

    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")

    return parsed


def log_level_env(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "INFO").upper()
    if value == "WARN":
        value = "WARNING"

    if value not in VALID_LOG_LEVELS:
        raise ValueError(f"{name} must be one of {', '.join(sorted(VALID_LOG_LEVELS))}")

    return value
