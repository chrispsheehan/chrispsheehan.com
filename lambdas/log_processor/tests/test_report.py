import gzip
from datetime import datetime, timezone
from hashlib import md5
from io import BytesIO
import json

from botocore.exceptions import ClientError

from lambdas.log_processor.config import LogProcessorConfig
from lambdas.log_processor.ledger import lock_key, object_id
from lambdas.log_processor.logs_processor import LocalS3OutputClient, logs_report
from lambdas.log_processor.output_writer import SUMMARY_KEY
from lambdas.log_processor.lambda_handler import handle_event


def _config(max_files=None):
    return LogProcessorConfig(
        report_bucket_name="report-bucket",
        database_bucket_name="database-bucket",
        logs_bucket_name="logs-bucket",
        logs_prefix="cloudfront/",
        max_files=max_files,
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
        if bucket == "database-bucket":
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
        if Bucket == "database-bucket":
            body = self.report_bodies[Key]
            if isinstance(body, str):
                body = body.encode("utf-8")
            return {"Body": FakeBody(body)}
        raise AssertionError(f"Unexpected bucket: {Bucket}")

    def put_object(self, **kwargs):
        self.puts.append(kwargs)
        if kwargs["Bucket"] != "database-bucket":
            return {}

        key = kwargs["Key"]
        if kwargs.get("IfNoneMatch") == "*" and key in self.report_bodies:
            raise _client_error("PreconditionFailed")

        if_match = kwargs.get("IfMatch")
        if if_match is not None and self._report_etag(key) != if_match:
            raise _client_error("PreconditionFailed")

        self.report_bodies[key] = kwargs["Body"]
        return {"ETag": f'"{self._report_etag(key)}"'}

    def head_object(self, *, Bucket, Key):
        if Bucket != "database-bucket":
            raise AssertionError(f"Unexpected bucket: {Bucket}")
        if Key not in self.report_bodies:
            raise _client_error("404")
        return {"ETag": f'"{self._report_etag(Key)}"'}

    def _report_etag(self, key):
        body = self.report_bodies[key]
        if isinstance(body, str):
            body = body.encode("utf-8")
        return md5(body).hexdigest()


def _object(key, etag, day):
    return {
        "Key": key,
        "ETag": f'"{etag}"',
        "LastModified": datetime(2026, 1, day, tzinfo=timezone.utc),
        "Size": 100,
    }


def _gzip_body(*rows):
    return gzip.compress("".join(rows).encode("utf-8"))


def _client_error(code):
    return ClientError({"Error": {"Code": code}}, "PutObject")


def _completed_lock(bucket, obj):
    claimed_object_id = object_id(bucket, obj["Key"], obj["ETag"].strip('"'))
    return (
        lock_key(claimed_object_id),
        json.dumps({"object_id": claimed_object_id, "status": "complete"}),
    )


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
    s3 = FakeS3(objects, bodies, report_bodies=dict([_completed_lock("logs-bucket", objects[1])]))

    summary = logs_report("database-bucket", config=_config(), s3_client=s3)

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

    assert [put["ContentType"] for put in s3.puts if put["ContentType"] == "application/x-ndjson"] == [
        "application/x-ndjson",
        "application/x-ndjson",
    ]
    first_record_put = next(put for put in s3.puts if put["ContentType"] == "application/x-ndjson")
    first_record = json.loads(first_record_put["Body"].splitlines()[0])
    assert first_record["viewer_ip"] == "203.0.113.10"
    complete_locks = [
        json.loads(body)
        for key, body in s3.report_bodies.items()
        if key.startswith("data/log-processor/locks/")
        and json.loads(body)["status"] == "complete"
    ]
    assert len(complete_locks) == 2
    assert any(lock.get("record_count") == 3 for lock in complete_locks)


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

    summary = logs_report("database-bucket", config=_config(max_files=1), s3_client=s3)

    assert summary["log-files-found"] == 2
    assert summary["log-files-limit"] == 1
    assert summary["log-files-claimed"] == 1
    assert summary["log-files-processed"] == 1
    assert len([put for put in s3.puts if put.get("IfNoneMatch") == "*"]) == 1


def test_logs_report_builds_visit_summary_from_existing_database_files():
    objects = [_object("cloudfront/skipped.gz", "etag-1", 1)]
    s3 = FakeS3(
        objects,
        {},
        report_bodies={
            _completed_lock("logs-bucket", objects[0])[0]: _completed_lock("logs-bucket", objects[0])[1],
            "data/log-processor/requests/date=2026-01-01/existing.jsonl": (
                '{"date":"2026-01-01","viewer_ip":"203.0.113.10"}\n'
                '{"date":"2026-01-01","viewer_ip":"203.0.113.10"}\n'
                '{"date":"2026-01-02","viewer_ip":"203.0.113.20"}\n'
            )
        },
    )

    summary = logs_report("database-bucket", config=_config(), s3_client=s3)

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
    env = {
        "REPORT_BUCKET": "report-bucket",
        "DATABASE_BUCKET": "database-bucket",
        "S3_LOGS_BUCKET": "logs-bucket",
        "S3_LOGS_PREFIX": "cloudfront/",
    }

    response = handle_event({}, None, s3_client=s3, env=env)

    assert response["statusCode"] == 200
    response_body = json.loads(response["body"])
    assert response_body["s3_path"] == f"s3://report-bucket/{SUMMARY_KEY}"
    assert len(response_body["output-keys"]) == 1
    assert response_body["run-output-keys"] == response_body["output-keys"]
    assert s3.puts[-1]["Key"] == SUMMARY_KEY
    assert s3.puts[-1]["ContentType"] == "application/json"
    public_summary = json.loads(s3.puts[-1]["Body"])
    assert "output-keys" not in public_summary
    assert "run-output-keys" not in public_summary
    assert public_summary["total-visits"] == 1


def test_local_s3_output_client_writes_objects_under_key_path(tmp_path):
    client = LocalS3OutputClient(
        FakeS3([], {}),
        tmp_path,
        "database-bucket",
    )

    client.put_object(
        Bucket="database-bucket",
        Key="data/log-processor/requests/date=2026-01-01/source.jsonl",
        Body='{"viewer_ip":"203.0.113.10"}\n',
        ContentType="application/x-ndjson",
    )

    assert (
        tmp_path / "data/log-processor/requests/date=2026-01-01/source.jsonl"
    ).read_text(encoding="utf-8") == '{"viewer_ip":"203.0.113.10"}\n'
    pages = list(
        client.get_paginator("list_objects_v2").paginate(
            Bucket="database-bucket",
            Prefix="data/log-processor/requests/",
        )
    )
    assert pages[0]["Contents"][0]["Key"] == "data/log-processor/requests/date=2026-01-01/source.jsonl"
    response = client.get_object(
        Bucket="database-bucket",
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

    with caplog.at_level("INFO"):
        logs_report("database-bucket", config=_config(), s3_client=s3)

    messages = [record.getMessage() for record in caplog.records]
    assert any("Found 2 CloudFront log object(s)" in message for message in messages)
    assert any("Processing claimed log file 1/2 key=cloudfront/one.gz" in message for message in messages)
    assert any("Completed log file 2/2 key=cloudfront/two.gz" in message for message in messages)
    assert any("Finished log processor run found=2 claimed=2 processed=2" in message for message in messages)
