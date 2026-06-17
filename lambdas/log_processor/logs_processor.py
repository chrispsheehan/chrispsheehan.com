from __future__ import annotations

import argparse
import json
from typing import Any

try:
    from .aws_clients import create_dynamodb_client, create_s3_client
    from .config import LogProcessorConfig, load_config
    from .report import process_logs
except ImportError:
    from aws_clients import create_dynamodb_client, create_s3_client
    from config import LogProcessorConfig, load_config
    from report import process_logs


def logs_report(
    report_bucket_name: str,
    *,
    config: LogProcessorConfig | None = None,
    s3_client: Any | None = None,
    dynamodb_client: Any | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    config = config or load_config(report_bucket_name=report_bucket_name, env=env)
    s3_client = s3_client or create_s3_client()
    dynamodb_client = dynamodb_client or create_dynamodb_client(config)

    return process_logs(config, s3_client, dynamodb_client)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run logs_report(report_bucket_name) directly.")
    parser.add_argument(
        "report_bucket_name",
        help="S3 database bucket passed directly to logs_report(report_bucket_name).",
    )
    args = parser.parse_args()

    report = logs_report(args.report_bucket_name)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    _main()
