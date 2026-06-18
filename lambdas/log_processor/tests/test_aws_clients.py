from lambdas.log_processor.aws_clients import dynamodb_client_kwargs
from lambdas.log_processor.config import LogProcessorConfig


def _config(endpoint, access_key=None, secret_key=None):
    return LogProcessorConfig(
        report_bucket_name="report-bucket",
        logs_bucket_name="logs-bucket",
        logs_prefix="",
        max_files=None,
        processed_log_files_table="processed-files",
        dynamodb_region="eu-west-2",
        dynamodb_endpoint=endpoint,
        dynamodb_access_key_id=access_key,
        dynamodb_secret_access_key=secret_key,
        log_level="INFO",
    )


def test_dynamodb_client_kwargs_use_dummy_credentials_for_local_endpoint():
    kwargs = dynamodb_client_kwargs(_config("http://dynamodb-local:8000"))

    assert kwargs["aws_access_key_id"] == "DUMMYIDEXAMPLE"
    assert kwargs["aws_secret_access_key"] == "DUMMYEXAMPLEKEY"


def test_dynamodb_client_kwargs_use_boto3_chain_for_aws_endpoint():
    kwargs = dynamodb_client_kwargs(_config("https://dynamodb.eu-west-2.amazonaws.com"))

    assert "aws_access_key_id" not in kwargs
    assert "aws_secret_access_key" not in kwargs


def test_dynamodb_client_kwargs_allow_explicit_credentials():
    kwargs = dynamodb_client_kwargs(
        _config(
            "https://dynamodb.eu-west-2.amazonaws.com",
            access_key="access",
            secret_key="secret",
        )
    )

    assert kwargs["aws_access_key_id"] == "access"
    assert kwargs["aws_secret_access_key"] == "secret"
