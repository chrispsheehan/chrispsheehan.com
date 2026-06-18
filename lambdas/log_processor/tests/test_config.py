import pytest

from lambdas.log_processor.config import (
    load_config,
    log_level_env,
    optional_positive_int_env,
    required_env,
)


BASE_ENV = {
    "REPORT_BUCKET": "report-bucket",
    "S3_LOGS_BUCKET": "logs-bucket",
    "PROCESSED_LOG_FILES_TABLE": "processed-files",
    "DYNAMODB_AWS_REGION": "eu-west-2",
    "DYNAMODB_ENDPOINT": "http://localhost:8000",
}


def test_load_config_reads_required_and_optional_values():
    env = {
        **BASE_ENV,
        "S3_LOGS_PREFIX": "cloudfront/",
        "S3_LOGS_MAX_FILES": "10",
        "DYNAMODB_AWS_ACCESS_KEY_ID": "access",
        "DYNAMODB_AWS_SECRET_ACCESS_KEY": "secret",
        "LOG_LEVEL": "debug",
    }

    config = load_config(env=env)

    assert config.report_bucket_name == "report-bucket"
    assert config.logs_bucket_name == "logs-bucket"
    assert config.logs_prefix == "cloudfront/"
    assert config.max_files == 10
    assert config.processed_log_files_table == "processed-files"
    assert config.dynamodb_access_key_id == "access"
    assert config.dynamodb_secret_access_key == "secret"
    assert config.log_level == "DEBUG"


def test_load_config_allows_report_bucket_override_and_defaults():
    config = load_config(report_bucket_name="override-bucket", env=BASE_ENV)

    assert config.report_bucket_name == "override-bucket"
    assert config.logs_prefix == ""
    assert config.max_files is None
    assert config.dynamodb_access_key_id == "DUMMYIDEXAMPLE"
    assert config.dynamodb_secret_access_key == "DUMMYEXAMPLEKEY"
    assert config.log_level == "INFO"


def test_required_env_rejects_missing_values():
    with pytest.raises(ValueError, match="REPORT_BUCKET must be set"):
        required_env({}, "REPORT_BUCKET")


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_optional_positive_int_env_rejects_invalid_values(value):
    with pytest.raises(ValueError, match="S3_LOGS_MAX_FILES must be a positive integer"):
        optional_positive_int_env({"S3_LOGS_MAX_FILES": value}, "S3_LOGS_MAX_FILES")


def test_log_level_env_allows_warn_alias():
    assert log_level_env({"LOG_LEVEL": "warn"}, "LOG_LEVEL") == "WARNING"


def test_log_level_env_rejects_invalid_values():
    with pytest.raises(ValueError, match="LOG_LEVEL must be one of"):
        log_level_env({"LOG_LEVEL": "chatty"}, "LOG_LEVEL")
