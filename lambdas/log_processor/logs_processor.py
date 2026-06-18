from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

try:
    from .aws_clients import create_dynamodb_client, create_s3_client
    from .config import LogProcessorConfig, load_config
    from .logging_config import configure_logging
    from .report import process_logs
except ImportError:
    from aws_clients import create_dynamodb_client, create_s3_client
    from config import LogProcessorConfig, load_config
    from logging_config import configure_logging
    from report import process_logs

logger = logging.getLogger(__name__)


class NoWriteS3Client:
    def __init__(self, wrapped: Any) -> None:
        self._wrapped = wrapped

    def put_object(self, **_: Any) -> dict[str, Any]:
        return {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)


def logs_report(
    report_bucket_name: str,
    *,
    config: LogProcessorConfig | None = None,
    s3_client: Any | None = None,
    dynamodb_client: Any | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    config = config or load_config(report_bucket_name=report_bucket_name, env=env)
    configure_logging(config.log_level)

    logger.info(
        "Preparing log processor report logs_bucket=%s logs_prefix=%s report_bucket=%s max_files=%s",
        config.logs_bucket_name,
        config.logs_prefix,
        config.report_bucket_name,
        config.max_files,
    )

    s3_client = s3_client or create_s3_client()
    dynamodb_client = dynamodb_client or create_dynamodb_client(config)

    return process_logs(config, s3_client, dynamodb_client)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run logs_report(report_bucket_name) directly.")
    parser.add_argument(
        "report_bucket_name",
        help="S3 database bucket passed directly to logs_report(report_bucket_name).",
    )
    parser.add_argument(
        "--suppress-s3-writes",
        action="store_true",
        help="Read source logs normally but suppress report bucket writes.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="Write the summary JSON to this local path instead of stdout.",
    )
    args = parser.parse_args()

    s3_client = create_s3_client()
    if args.suppress_s3_writes:
        s3_client = NoWriteS3Client(s3_client)

    report = logs_report(args.report_bucket_name, s3_client=s3_client)
    output = json.dumps(report, indent=2, sort_keys=True)

    print(output)

    if args.summary_output is not None:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(f"{output}\n", encoding="utf-8")


if __name__ == "__main__":
    _main()
