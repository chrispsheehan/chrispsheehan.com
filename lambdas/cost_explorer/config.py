from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


@dataclass(frozen=True)
class CostExplorerConfig:
    report_bucket_name: str
    project_name: str
    environment_name: str


def load_config(*, env: Mapping[str, str] | None = None) -> CostExplorerConfig:
    env = env or os.environ

    return CostExplorerConfig(
        report_bucket_name=required_env(env, "REPORT_BUCKET"),
        project_name=required_env(env, "PROJECT_NAME"),
        environment_name=required_env(env, "ENVIRONMENT_NAME"),
    )


def required_env(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if not value:
        raise ValueError(f"{name} must be set")
    return value
