from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lambdas.log_processor.cloudfront_logs import LogObject
from lambdas.log_processor.ledger import (
    claim_log_object,
    mark_complete,
    mark_failed,
    object_id,
)


class FakeDynamoDB:
    class exceptions:
        class ConditionalCheckFailedException(Exception):
            pass

    def __init__(self, existing_item=None):
        self.item = existing_item
        self.puts = []
        self.updates = []

    def put_item(self, **kwargs):
        self.puts.append(kwargs)
        existing = self.item
        now = kwargs["ExpressionAttributeValues"][":now"]["S"]

        if existing is not None:
            status = existing["status"]["S"]
            expires_at = existing.get("processing_expires_at", {}).get("S")
            can_claim = status == "failed" or (
                status == "processing" and expires_at is not None and expires_at < now
            )
            if not can_claim:
                raise self.exceptions.ConditionalCheckFailedException()

        self.item = kwargs["Item"]

    def update_item(self, **kwargs):
        self.updates.append(kwargs)


def _log_object():
    return LogObject(
        key="cloudfront/example.gz",
        etag="etag-1",
        last_modified="2026-01-01T00:00:00+00:00",
        size=100,
    )


def _existing_item(status, *, expires_at=None):
    item = {
        "object_id": {"S": object_id("logs-bucket", _log_object().key, _log_object().etag)},
        "status": {"S": status},
    }
    if expires_at is not None:
        item["processing_expires_at"] = {"S": expires_at.isoformat()}
    return item


def test_claim_log_object_sets_processing_lease():
    dynamodb = FakeDynamoDB()

    claimed_object_id = claim_log_object(
        dynamodb,
        "processed-files",
        "logs-bucket",
        _log_object(),
    )

    assert claimed_object_id == object_id("logs-bucket", _log_object().key, _log_object().etag)
    item = dynamodb.item
    assert item["status"] == {"S": "processing"}
    assert item["processing_expires_at"]["S"] > item["claimed_at"]["S"]
    assert dynamodb.puts[0]["ConditionExpression"] == (
        "attribute_not_exists(object_id) OR "
        "#status = :failed OR "
        "(#status = :processing AND processing_expires_at < :now)"
    )


def test_claim_log_object_does_not_steal_active_processing_lease():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    dynamodb = FakeDynamoDB(_existing_item("processing", expires_at=future))

    claimed_object_id = claim_log_object(
        dynamodb,
        "processed-files",
        "logs-bucket",
        _log_object(),
    )

    assert claimed_object_id is None


def test_claim_log_object_reclaims_expired_processing_lease():
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    dynamodb = FakeDynamoDB(_existing_item("processing", expires_at=past))

    claimed_object_id = claim_log_object(
        dynamodb,
        "processed-files",
        "logs-bucket",
        _log_object(),
    )

    assert claimed_object_id == object_id("logs-bucket", _log_object().key, _log_object().etag)
    assert dynamodb.item["status"] == {"S": "processing"}


def test_claim_log_object_reclaims_failed_item():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    dynamodb = FakeDynamoDB(_existing_item("failed", expires_at=future))

    claimed_object_id = claim_log_object(
        dynamodb,
        "processed-files",
        "logs-bucket",
        _log_object(),
    )

    assert claimed_object_id == object_id("logs-bucket", _log_object().key, _log_object().etag)


def test_terminal_updates_remove_processing_lease():
    dynamodb = FakeDynamoDB()
    claimed_object_id = object_id("logs-bucket", _log_object().key, _log_object().etag)

    mark_complete(dynamodb, "processed-files", claimed_object_id, 3, ["output.jsonl"])
    mark_failed(dynamodb, "processed-files", claimed_object_id, RuntimeError("failed"))

    assert "REMOVE #error, processing_expires_at" in dynamodb.updates[0]["UpdateExpression"]
    assert "REMOVE processing_expires_at" in dynamodb.updates[1]["UpdateExpression"]
