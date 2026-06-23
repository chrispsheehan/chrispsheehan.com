from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import md5
from io import BytesIO
import json

from botocore.exceptions import ClientError

from lambdas.log_processor.cloudfront_logs import LogObject
from lambdas.log_processor.ledger import (
    ClaimDecision,
    LOCKS_PREFIX,
    LockClaim,
    claim_log_object,
    lock_key,
    mark_complete,
    mark_failed,
    object_id,
)


class FakeS3:
    def __init__(self, objects=None):
        self.objects = dict(objects or {})
        self.puts = []

    def put_object(self, **kwargs):
        self.puts.append(kwargs)
        key = kwargs["Key"]

        if kwargs.get("IfNoneMatch") == "*" and key in self.objects:
            raise _client_error("PreconditionFailed")

        if_match = kwargs.get("IfMatch")
        if if_match is not None and self._etag(key) != if_match:
            raise _client_error("PreconditionFailed")

        body = kwargs["Body"]
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.objects[key] = body
        return {"ETag": f'"{md5(body).hexdigest()}"'}

    def head_object(self, **kwargs):
        key = kwargs["Key"]
        if key not in self.objects:
            raise _client_error("404")
        return {"ETag": f'"{self._etag(key)}"'}

    def get_object(self, **kwargs):
        key = kwargs["Key"]
        if key not in self.objects:
            raise _client_error("404")
        return {"Body": BytesIO(self.objects[key])}

    def _etag(self, key):
        return md5(self.objects[key]).hexdigest()


def _client_error(code):
    return ClientError({"Error": {"Code": code}}, "PutObject")


def _log_object():
    return LogObject(
        key="cloudfront/example.gz",
        etag="etag-1",
        last_modified="2026-01-01T00:00:00+00:00",
        size=100,
    )


def _object_id():
    return object_id("logs-bucket", _log_object().key, _log_object().etag)


def _lock_body(status, *, expires_at=None):
    body = {
        "object_id": _object_id(),
        "status": status,
    }
    if expires_at is not None:
        body["processing_expires_at"] = expires_at.isoformat()
    return json.dumps(body).encode("utf-8")


def test_claim_log_object_creates_processing_lock_with_if_none_match():
    s3 = FakeS3()

    claim = claim_log_object(
        s3,
        "report-bucket",
        "logs-bucket",
        _log_object(),
    )

    assert claim == ClaimDecision(
        status="claimed",
        claim=LockClaim(_object_id(), lock_key(_object_id()), claim.claim.etag),
    )
    assert claim.claim is not None
    assert claim.claim.lock_key == f"{LOCKS_PREFIX}{_object_id()}.json"
    lock = json.loads(s3.objects[claim.claim.lock_key])
    assert lock["status"] == "processing"
    assert lock["processing_expires_at"] > lock["claimed_at"]
    assert s3.puts[0]["IfNoneMatch"] == "*"


def test_claim_log_object_does_not_steal_active_processing_lock():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    s3 = FakeS3({lock_key(_object_id()): _lock_body("processing", expires_at=future)})

    claim = claim_log_object(
        s3,
        "report-bucket",
        "logs-bucket",
        _log_object(),
    )

    assert claim == ClaimDecision(status="busy")


def test_claim_log_object_reclaims_expired_processing_lock_with_if_match():
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    s3 = FakeS3({lock_key(_object_id()): _lock_body("processing", expires_at=past)})
    old_etag = s3._etag(lock_key(_object_id()))

    claim = claim_log_object(
        s3,
        "report-bucket",
        "logs-bucket",
        _log_object(),
    )

    assert claim == ClaimDecision(
        status="claimed",
        claim=LockClaim(_object_id(), lock_key(_object_id()), claim.claim.etag),
    )
    assert claim.claim is not None
    assert s3.puts[-1]["IfMatch"] == old_etag
    assert json.loads(s3.objects[claim.claim.lock_key])["status"] == "processing"


def test_claim_log_object_reclaims_failed_lock():
    s3 = FakeS3({lock_key(_object_id()): _lock_body("failed")})

    claim = claim_log_object(
        s3,
        "report-bucket",
        "logs-bucket",
        _log_object(),
    )

    assert claim == ClaimDecision(
        status="claimed",
        claim=LockClaim(_object_id(), lock_key(_object_id()), claim.claim.etag),
    )


def test_terminal_updates_use_claim_etag():
    s3 = FakeS3()
    claim = claim_log_object(s3, "report-bucket", "logs-bucket", _log_object())
    assert claim.claim is not None

    mark_complete(s3, "report-bucket", claim.claim, 3, ["output.jsonl"])
    complete = json.loads(s3.objects[claim.claim.lock_key])
    assert complete["status"] == "complete"
    assert complete["record_count"] == 3
    assert complete["output_keys"] == ["output.jsonl"]
    assert s3.puts[-1]["IfMatch"] == claim.claim.etag

    failed_claim = LockClaim(
        claim.claim.object_id,
        claim.claim.lock_key,
        s3._etag(claim.claim.lock_key),
    )
    mark_failed(s3, "report-bucket", failed_claim, RuntimeError("failed"))
    failed = json.loads(s3.objects[claim.claim.lock_key])
    assert failed["status"] == "failed"
    assert failed["error"] == "failed"
