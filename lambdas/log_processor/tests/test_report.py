import gzip
from datetime import datetime, timezone
from io import BytesIO
import json

from lambdas.log_processor.config import LogProcessorConfig
from lambdas.log_processor.logs_processor import LocalS3OutputClient, logs_report
from lambdas.log_processor.output_writer import SUMMARY_KEY
from lambdas.log_processor.lambda_handler import handle_event


def _config(max_files=None):
    return LogProcessorConfig(
        report_bucket_name="report-bucket",
        logs_bucket_name="logs-bucket",
        logs_prefix="cloudfront/",
        max_files=max_files,
        processed_log_files_table="processed-files",
        dynamodb_region="eu-west-2",
        dynamodb_endpoint="http://localhost:8000",
        dynamodb_access_key_id="access",
        dynamodb_secret_access_key="secret",
        log_level="INFO",
    )


def _row(date, viewer_ip, request_id, user_agent="Mozilla/5.0"):
    return (
        f"{date}\t12:00:00\tLHR\t123\t{viewer_ip}\tGET\texample.com\t"
        f"/path\t200\t-\t{user_agent}\t-\t-\tHit\t{request_id}\n"
    )


class FakeBody(BytesIO):
    pass


class FakePaginator:
    def __init__(self, s3):
        self.s3 = s3

    def paginate(self, **kwargs):
        bucket = kwargs["Bucket"]
        prefix = kwargs.get("Prefix", "")
        if bucket == "logs-bucket":
            return [{"Contents": [obj for obj in self.s3.objects if obj["Key"].startswith(prefix)]}]
        if bucket == "report-bucket":
            return [
                {
                    "Contents": [
                        {
                            "Key": key,
                            "LastModified": datetime(2026, 1, 1, tzinfo=timezone.utc),
                            "Size": len(body),
                        }
                        for key, body in self.s3.report_bodies.items()
                        if key.startswith(prefix)
                    ]
                }
            ]
        return [{"Contents": []}]


class FakeS3:
    def __init__(self, objects, bodies, report_bodies=None):
        self.objects = objects
        self.bodies = bodies
        self.report_bodies = dict(report_bodies or {})
        self.puts = []

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return FakePaginator(self)

    def get_object(self, *, Bucket, Key):
        if Bucket == "logs-bucket":
            return {"Body": FakeBody(self.bodies[Key])}
        if Bucket == "report-bucket":
            body = self.report_bodies[Key]
            if isinstance(body, str):
                body = body.encode("utf-8")
            return {"Body": FakeBody(body)}
        raise AssertionError(f"Unexpected bucket: {Bucket}")

    def put_object(self, **kwargs):
        self.puts.append(kwargs)
        if kwargs["Bucket"] == "report-bucket":
            self.report_bodies[kwargs["Key"]] = kwargs["Body"]


class FakeDynamoDB:
    class exceptions:
        class ConditionalCheckFailedException(Exception):
            pass

    def __init__(self, skip_keys=None):
        self.skip_keys = set(skip_keys or [])
        self.puts = []
        self.updates = []

    def put_item(self, **kwargs):
        self.puts.append(kwargs)
        if kwargs["Item"]["source_key"]["S"] in self.skip_keys:
            raise self.exceptions.ConditionalCheckFailedException()

    def update_item(self, **kwargs):
        self.updates.append(kwargs)


def _object(key, etag, day):
    return {
        "Key": key,
        "ETag": f'"{etag}"',
        "LastModified": datetime(2026, 1, day, tzinfo=timezone.utc),
        "Size": 100,
    }


def _gzip_body(*rows):
    return gzip.compress("".join(rows).encode("utf-8"))


def test_logs_report_processes_claimed_logs_and_writes_jsonl():
    objects = [
        _object("cloudfront/processed.gz", "etag-1", 1),
        _object("cloudfront/skipped.gz", "etag-2", 2),
    ]
    bodies = {
        "cloudfront/processed.gz": _gzip_body(
            _row("2026-01-01", "203.0.113.10", "req-1"),
            _row("2026-01-01", "203.0.113.10", "req-2"),
            _row("2026-01-02", "203.0.113.20", "req-3"),
            _row("2026-01-02", "203.0.113.30", "bot-1", "Googlebot"),
        )
    }
    s3 = FakeS3(objects, bodies)
    dynamodb = FakeDynamoDB(skip_keys={"cloudfront/skipped.gz"})

    summary = logs_report("report-bucket", config=_config(), s3_client=s3, dynamodb_client=dynamodb)

    assert summary["daily-visits"] == 1
    assert summary["total-visits"] == 2
    assert summary["range"] == 2
    assert summary["last-date"] == "2026-01-02"
    assert summary["log-files-found"] == 2
    assert summary["log-files-claimed"] == 1
    assert summary["log-files-processed"] == 1
    assert summary["log-files-skipped"] == 1
    assert summary["log-files-failed"] == 0
    assert len(summary["output-keys"]) == 2
    assert len(summary["run-output-keys"]) == 2

    assert [put["ContentType"] for put in s3.puts] == [
        "application/x-ndjson",
        "application/x-ndjson",
    ]
    first_record = json.loads(s3.puts[0]["Body"].splitlines()[0])
    assert first_record["viewer_ip"] == "203.0.113.10"
    assert dynamodb.updates[0]["ExpressionAttributeValues"][":status"] == {"S": "complete"}
    assert dynamodb.updates[0]["ExpressionAttributeValues"][":record_count"] == {"N": "3"}


def test_logs_report_respects_max_claimed_files():
    objects = [
        _object("cloudfront/one.gz", "etag-1", 1),
        _object("cloudfront/two.gz", "etag-2", 2),
    ]
    bodies = {
        "cloudfront/one.gz": _gzip_body(_row("2026-01-01", "203.0.113.10", "req-1")),
        "cloudfront/two.gz": _gzip_body(_row("2026-01-02", "203.0.113.20", "req-2")),
    }
    s3 = FakeS3(objects, bodies)
    dynamodb = FakeDynamoDB()

    summary = logs_report("report-bucket", config=_config(max_files=1), s3_client=s3, dynamodb_client=dynamodb)

    assert summary["log-files-found"] == 2
    assert summary["log-files-limit"] == 1
    assert summary["log-files-claimed"] == 1
    assert summary["log-files-processed"] == 1
    assert len(dynamodb.puts) == 1


def test_logs_report_builds_visit_summary_from_existing_database_files():
    objects = [_object("cloudfront/skipped.gz", "etag-1", 1)]
    s3 = FakeS3(
        objects,
        {},
        report_bodies={
            "data/log-processor/requests/date=2026-01-01/existing.jsonl": (
                '{"date":"2026-01-01","viewer_ip":"203.0.113.10"}\n'
                '{"date":"2026-01-01","viewer_ip":"203.0.113.10"}\n'
                '{"date":"2026-01-02","viewer_ip":"203.0.113.20"}\n'
            )
        },
    )
    dynamodb = FakeDynamoDB(skip_keys={"cloudfront/skipped.gz"})

    summary = logs_report("report-bucket", config=_config(), s3_client=s3, dynamodb_client=dynamodb)

    assert summary["daily-visits"] == 1
    assert summary["total-visits"] == 2
    assert summary["range"] == 2
    assert summary["last-date"] == "2026-01-02"
    assert summary["log-files-processed"] == 0
    assert len(summary["output-keys"]) == 1
    assert summary["run-output-keys"] == []


def test_handle_event_writes_summary_with_injected_clients():
    objects = [_object("cloudfront/one.gz", "etag-1", 1)]
    bodies = {
        "cloudfront/one.gz": _gzip_body(_row("2026-01-01", "203.0.113.10", "req-1")),
    }
    s3 = FakeS3(objects, bodies)
    dynamodb = FakeDynamoDB()
    env = {
        "REPORT_BUCKET": "report-bucket",
        "S3_LOGS_BUCKET": "logs-bucket",
        "S3_LOGS_PREFIX": "cloudfront/",
        "PROCESSED_LOG_FILES_TABLE": "processed-files",
        "DYNAMODB_AWS_REGION": "eu-west-2",
        "DYNAMODB_ENDPOINT": "http://localhost:8000",
    }

    response = handle_event({}, None, s3_client=s3, dynamodb_client=dynamodb, env=env)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"s3_path": f"s3://report-bucket/{SUMMARY_KEY}"}
    assert s3.puts[-1]["Key"] == SUMMARY_KEY
    assert s3.puts[-1]["ContentType"] == "application/json"


def test_local_s3_output_client_writes_objects_under_key_path(tmp_path):
    client = LocalS3OutputClient(
        FakeS3([], {}),
        tmp_path,
        "report-bucket",
    )

    client.put_object(
        Bucket="report-bucket",
        Key="data/log-processor/requests/date=2026-01-01/source.jsonl",
        Body='{"viewer_ip":"203.0.113.10"}\n',
        ContentType="application/x-ndjson",
    )

    assert (
        tmp_path / "data/log-processor/requests/date=2026-01-01/source.jsonl"
    ).read_text(encoding="utf-8") == '{"viewer_ip":"203.0.113.10"}\n'
    pages = list(
        client.get_paginator("list_objects_v2").paginate(
            Bucket="report-bucket",
            Prefix="data/log-processor/requests/",
        )
    )
    assert pages[0]["Contents"][0]["Key"] == "data/log-processor/requests/date=2026-01-01/source.jsonl"
    response = client.get_object(
        Bucket="report-bucket",
        Key="data/log-processor/requests/date=2026-01-01/source.jsonl",
    )
    assert response["Body"].read().decode("utf-8") == '{"viewer_ip":"203.0.113.10"}\n'


def test_logs_report_logs_progress_for_each_file(caplog):
    objects = [
        _object("cloudfront/one.gz", "etag-1", 1),
        _object("cloudfront/two.gz", "etag-2", 2),
    ]
    bodies = {
        "cloudfront/one.gz": _gzip_body(_row("2026-01-01", "203.0.113.10", "req-1")),
        "cloudfront/two.gz": _gzip_body(_row("2026-01-02", "203.0.113.20", "req-2")),
    }
    s3 = FakeS3(objects, bodies)
    dynamodb = FakeDynamoDB()

    with caplog.at_level("INFO"):
        logs_report("report-bucket", config=_config(), s3_client=s3, dynamodb_client=dynamodb)

    messages = [record.getMessage() for record in caplog.records]
    assert any("Found 2 CloudFront log object(s)" in message for message in messages)
    assert any("Processing claimed log file 1/2 key=cloudfront/one.gz" in message for message in messages)
    assert any("Completed log file 2/2 key=cloudfront/two.gz" in message for message in messages)
    assert any("Finished log processor run found=2 claimed=2 processed=2" in message for message in messages)
