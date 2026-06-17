import gzip
from datetime import datetime, timezone
from io import BytesIO
import json

from lambdas.log_processor.config import LogProcessorConfig
from lambdas.log_processor.logs_processor import logs_report
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
    )


def _row(date, viewer_ip, request_id, user_agent="Mozilla/5.0"):
    return (
        f"{date}\t12:00:00\tLHR\t123\t{viewer_ip}\tGET\texample.com\t"
        f"/path\t200\t-\t{user_agent}\t-\t-\tHit\t{request_id}\n"
    )


class FakeBody(BytesIO):
    pass


class FakePaginator:
    def __init__(self, objects):
        self.objects = objects

    def paginate(self, **kwargs):
        return [{"Contents": self.objects}]


class FakeS3:
    def __init__(self, objects, bodies):
        self.objects = objects
        self.bodies = bodies
        self.puts = []

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return FakePaginator(self.objects)

    def get_object(self, *, Bucket, Key):
        assert Bucket == "logs-bucket"
        return {"Body": FakeBody(self.bodies[Key])}

    def put_object(self, **kwargs):
        self.puts.append(kwargs)


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
