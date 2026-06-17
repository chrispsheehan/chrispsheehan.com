import sys
import json

try:
    from .aws_clients import create_dynamodb_client, create_s3_client
    from .config import load_config
    from .logs_processor import logs_report
    from .output_writer import SUMMARY_KEY, write_summary
except ImportError:
    from aws_clients import create_dynamodb_client, create_s3_client
    from config import load_config
    from logs_processor import logs_report
    from output_writer import SUMMARY_KEY, write_summary


def handle_event(event, context, *, s3_client=None, dynamodb_client=None, env=None):
    config = load_config(env=env)
    s3_client = s3_client or create_s3_client()
    dynamodb_client = dynamodb_client or create_dynamodb_client(config)

    combined = logs_report(
        config.report_bucket_name,
        config=config,
        s3_client=s3_client,
        dynamodb_client=dynamodb_client,
    )

    write_summary(s3_client, config.report_bucket_name, combined)
    s3_path = f"s3://{config.report_bucket_name}/{SUMMARY_KEY}"

    print(f"Log processed and saved to {s3_path}")
    return {"statusCode": 200, "body": json.dumps({"s3_path": s3_path})}


def lambda_handler(event, context):
    try:
        return handle_event(event, context)
    except Exception as exc:
        error_msg = f"Logs processor Lambda failed: {exc}"
        print(error_msg, file=sys.stderr)

        # Return 500 JSON for API Gateway / test invocations
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}


if __name__ == "__main__":
    result = lambda_handler({}, None)
    if result.get("statusCode") != 200:
        sys.exit(1)
