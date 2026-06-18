from datetime import datetime, timezone

from lambdas.log_processor.cloudfront_logs import list_log_objects, parse_log_line


class FakePaginator:
    def paginate(self, **kwargs):
        assert kwargs == {"Bucket": "logs-bucket", "Prefix": "cloudfront/"}
        return [
            {
                "Contents": [
                    {
                        "Key": "cloudfront/b.gz",
                        "ETag": '"etag-b"',
                        "LastModified": datetime(2026, 1, 2, tzinfo=timezone.utc),
                        "Size": 20,
                    },
                    {
                        "Key": "cloudfront/a.gz",
                        "ETag": '"etag-a"',
                        "LastModified": datetime(2026, 1, 1, tzinfo=timezone.utc),
                        "Size": 10,
                    },
                    {
                        "Key": "cloudfront/ignored.txt",
                        "ETag": '"etag-c"',
                        "LastModified": datetime(2026, 1, 3, tzinfo=timezone.utc),
                        "Size": 30,
                    },
                ]
            }
        ]


class FakeS3:
    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return FakePaginator()


def test_list_log_objects_filters_gzip_and_sorts_oldest_first():
    objects = list_log_objects(FakeS3(), "logs-bucket", "cloudfront/")

    assert [obj.key for obj in objects] == ["cloudfront/a.gz", "cloudfront/b.gz"]
    assert objects[0].etag == "etag-a"
    assert objects[0].last_modified == "2026-01-01T00:00:00+00:00"
    assert objects[0].size == 10


def test_parse_log_line_returns_decoded_non_bot_record():
    line = (
        "2026-01-02\t12:00:00\tLHR\t123\t203.0.113.10\tGET\texample.com\t"
        "/hello%20world\t200\thttps%3A%2F%2Fref.example\tMozilla%2F5.0\t"
        "a%3D1\t-\tHit\treq-1\n"
    )

    record = parse_log_line(line, "cloudfront/a.gz")

    assert record == {
        "date": "2026-01-02",
        "time": "12:00:00",
        "edge_location": "LHR",
        "bytes_sent": 123,
        "viewer_ip": "203.0.113.10",
        "method": "GET",
        "host": "example.com",
        "uri": "/hello world",
        "status": 200,
        "referer": "https://ref.example",
        "user_agent": "Mozilla/5.0",
        "query": "a=1",
        "edge_result_type": "Hit",
        "request_id": "req-1",
        "source_key": "cloudfront/a.gz",
    }


def test_parse_log_line_ignores_comments_malformed_rows_and_bots():
    bot_line = (
        "2026-01-02\t12:00:00\tLHR\t123\t203.0.113.10\tGET\texample.com\t"
        "/\t200\t-\tGooglebot\t-\t-\tHit\treq-1\n"
    )

    assert parse_log_line("#Version: 1.0", "source.gz") is None
    assert parse_log_line("too\tshort", "source.gz") is None
    assert parse_log_line(bot_line, "source.gz") is None
