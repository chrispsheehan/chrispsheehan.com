from __future__ import annotations

import argparse
from hashlib import md5
import json
from pathlib import Path
from typing import Any

try:
    from .aws_clients import create_s3_client
    from .lambda_handler import handle_event
except ImportError:
    from aws_clients import create_s3_client
    from lambda_handler import handle_event


class NoWriteS3Client:
    def __init__(self, wrapped: Any) -> None:
        self._wrapped = wrapped

    def put_object(self, **_: Any) -> dict[str, Any]:
        return {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)


class LocalS3OutputClient(NoWriteS3Client):
    def __init__(self, wrapped: Any, output_dir: Path, report_bucket_name: str) -> None:
        super().__init__(wrapped)
        self._output_dir = output_dir
        self._report_bucket_name = report_bucket_name

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs["Bucket"] != self._report_bucket_name:
            return {}

        key = kwargs["Key"]
        body = kwargs.get("Body", b"")
        body_bytes = body if isinstance(body, bytes) else str(body).encode("utf-8")
        target = self._local_target(key)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body_bytes)
        return {"ETag": f'"{md5(body_bytes).hexdigest()}"'}

    def _local_target(self, key: str) -> Path:
        root = self._output_dir.resolve()
        target = (root / key).resolve()
        if root not in target.parents and target != root:
            raise ValueError(f"Refusing to access S3 key outside local output dir: {key}")
        return target


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run cost_explorer locally.")
    parser.add_argument(
        "report_bucket_name",
        help="S3 database bucket passed to the local cost explorer run.",
    )
    parser.add_argument(
        "--environment-name",
        default="dev",
        help="Environment tag used in the Cost Explorer filter.",
    )
    parser.add_argument(
        "--project-name",
        default="chrispsheehan.com",
        help="Project tag used in the Cost Explorer filter.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="Write the public summary JSON to this local path.",
    )
    parser.add_argument(
        "--local-s3-output-dir",
        type=Path,
        help="Write report bucket put_object payloads to this local directory instead of S3.",
    )
    parser.add_argument(
        "--suppress-s3-writes",
        action="store_true",
        help="Suppress report bucket writes.",
    )
    args = parser.parse_args()

    s3_client = create_s3_client()
    if args.local_s3_output_dir is not None:
        s3_client = LocalS3OutputClient(
            s3_client,
            args.local_s3_output_dir,
            args.report_bucket_name,
        )
    elif args.suppress_s3_writes:
        s3_client = NoWriteS3Client(s3_client)

    env = {
        "REPORT_BUCKET": args.report_bucket_name,
        "PROJECT_NAME": args.project_name,
        "ENVIRONMENT_NAME": args.environment_name,
    }
    result = handle_event({}, None, s3_client=s3_client, env=env)
    print(json.dumps(result, indent=2))

    if args.summary_output is not None:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        body = json.loads(result["body"])
        summary_path = body["s3_path"].split(f"s3://{args.report_bucket_name}/", 1)[1]
        local_summary = args.local_s3_output_dir / summary_path if args.local_s3_output_dir else None
        if local_summary is not None and local_summary.is_file():
            args.summary_output.write_text(local_summary.read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    _main()
