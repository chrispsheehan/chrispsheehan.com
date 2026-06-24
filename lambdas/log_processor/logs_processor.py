from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import md5
import json
import logging
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

try:
    from .aws_clients import create_s3_client
    from .config import LogProcessorConfig, load_config
    from .logging_config import configure_logging
    from .output_writer import OUTPUT_PREFIX, public_summary
    from .report import process_logs
except ImportError:
    from aws_clients import create_s3_client
    from config import LogProcessorConfig, load_config
    from logging_config import configure_logging
    from output_writer import OUTPUT_PREFIX, public_summary
    from report import process_logs

logger = logging.getLogger(__name__)


class NoWriteS3Client:
    def __init__(self, wrapped: Any) -> None:
        self._wrapped = wrapped

    def put_object(self, **_: Any) -> dict[str, Any]:
        return {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)


class LocalS3OutputClient(NoWriteS3Client):
    def __init__(self, wrapped: Any, output_dir: Path, database_bucket_name: str) -> None:
        super().__init__(wrapped)
        self._output_dir = output_dir
        self._database_bucket_name = database_bucket_name

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs["Bucket"] != self._database_bucket_name:
            return {}

        key = kwargs["Key"]
        body = kwargs.get("Body", b"")
        target = self._local_target(key)
        body_bytes = body if isinstance(body, bytes) else str(body).encode("utf-8")

        if kwargs.get("IfNoneMatch") == "*" and target.exists():
            raise s3_client_error("PreconditionFailed", "Object already exists")

        if_match = kwargs.get("IfMatch")
        if if_match is not None and (not target.exists() or local_etag(target) != if_match):
            raise s3_client_error("PreconditionFailed", "Object ETag does not match")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body_bytes)
        return {"ETag": f'"{md5(body_bytes).hexdigest()}"'}

    def get_paginator(self, name: str) -> Any:
        wrapped_paginator = self._wrapped.get_paginator(name)
        if name != "list_objects_v2":
            return wrapped_paginator
        return LocalS3OutputPaginator(wrapped_paginator, self._output_dir, self._database_bucket_name)

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if Bucket != self._database_bucket_name:
            return self._wrapped.get_object(Bucket=Bucket, Key=Key)

        target = self._local_target(Key)
        if not target.is_file():
            return self._wrapped.get_object(Bucket=Bucket, Key=Key)

        return {"Body": target.open("rb")}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if Bucket != self._database_bucket_name:
            return self._wrapped.head_object(Bucket=Bucket, Key=Key)

        target = self._local_target(Key)
        if not target.is_file():
            raise s3_client_error("404", "Object not found")

        stat = target.stat()
        return {
            "ETag": f'"{local_etag(target)}"',
            "LastModified": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
            "ContentLength": stat.st_size,
        }

    def _local_target(self, key: str) -> Path:
        root = self._output_dir.resolve()
        target = (root / key).resolve()
        if root not in target.parents and target != root:
            raise ValueError(f"Refusing to access S3 key outside local output dir: {key}")
        return target


class LocalS3OutputPaginator:
    def __init__(self, wrapped: Any, output_dir: Path, database_bucket_name: str) -> None:
        self._wrapped = wrapped
        self._output_dir = output_dir
        self._database_bucket_name = database_bucket_name

    def paginate(self, **kwargs: Any) -> Any:
        if kwargs.get("Bucket") != self._database_bucket_name:
            return self._wrapped.paginate(**kwargs)

        prefix = kwargs.get("Prefix", "")
        if prefix and not prefix.startswith(OUTPUT_PREFIX):
            return self._wrapped.paginate(**kwargs)

        root = self._output_dir.resolve()
        contents = []
        if root.is_dir():
            for path in sorted(item for item in root.rglob("*") if item.is_file()):
                key = path.relative_to(root).as_posix()
                if not key.startswith(prefix):
                    continue
                stat = path.stat()
                contents.append(
                    {
                        "Key": key,
                        "LastModified": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                        "Size": stat.st_size,
                    }
                )

        return [{"Contents": contents}]


def local_etag(path: Path) -> str:
    return md5(path.read_bytes()).hexdigest()


def s3_client_error(code: str, message: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": message}, "ResponseMetadata": {"HTTPStatusCode": 412}},
        "PutObject",
    )


def logs_report(
    database_bucket_name: str,
    *,
    config: LogProcessorConfig | None = None,
    s3_client: Any | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    config = config or load_config(database_bucket_name=database_bucket_name, env=env)
    configure_logging(config.log_level)

    logger.info(
        "Preparing log processor report logs_bucket=%s logs_prefix=%s database_bucket=%s report_bucket=%s max_files=%s",
        config.logs_bucket_name,
        config.logs_prefix,
        config.database_bucket_name,
        config.report_bucket_name,
        config.max_files,
    )

    s3_client = s3_client or create_s3_client()

    return process_logs(config, s3_client)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run logs_report(database_bucket_name) directly.")
    parser.add_argument(
        "database_bucket_name",
        help="S3 database bucket passed directly to logs_report(database_bucket_name).",
    )
    parser.add_argument(
        "--suppress-s3-writes",
        action="store_true",
        help="Read source logs normally but suppress database bucket writes.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="Write the summary JSON to this local path instead of stdout.",
    )
    parser.add_argument(
        "--local-s3-output-dir",
        type=Path,
        help="Write database bucket put_object payloads to this local directory instead of S3.",
    )
    args = parser.parse_args()

    s3_client = create_s3_client()
    if args.local_s3_output_dir is not None:
        s3_client = LocalS3OutputClient(s3_client, args.local_s3_output_dir, args.database_bucket_name)
    elif args.suppress_s3_writes:
        s3_client = NoWriteS3Client(s3_client)

    report = logs_report(args.database_bucket_name, s3_client=s3_client)
    output = json.dumps(report, indent=2, sort_keys=True)

    print(output)

    if args.summary_output is not None:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output = json.dumps(public_summary(report), indent=2, sort_keys=True)
        args.summary_output.write_text(f"{summary_output}\n", encoding="utf-8")


if __name__ == "__main__":
    _main()
