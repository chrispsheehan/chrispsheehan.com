import json
import logging
import sys

try:
    from .aws_clients import create_cost_explorer_client, create_s3_client
    from .config import load_config
    from .logging_config import configure_logging
    from .output_writer import SUMMARY_KEY, write_history, write_summary
    from .report import generate_cost_report
except ImportError:
    from aws_clients import create_cost_explorer_client, create_s3_client
    from config import load_config
    from logging_config import configure_logging
    from output_writer import SUMMARY_KEY, write_history, write_summary
    from report import generate_cost_report

logger = logging.getLogger(__name__)


def handle_event(event, context, *, cost_explorer_client=None, s3_client=None, env=None):
    config = load_config(env=env)
    configure_logging("INFO")

    request_id = getattr(context, "aws_request_id", None)
    logger.info(
        "Starting cost explorer invocation request_id=%s report_bucket=%s project=%s environment=%s",
        request_id,
        config.report_bucket_name,
        config.project_name,
        config.environment_name,
    )

    cost_explorer_client = cost_explorer_client or create_cost_explorer_client()
    s3_client = s3_client or create_s3_client()

    combined = generate_cost_report(
        config,
        cost_explorer_client=cost_explorer_client,
    )

    write_summary(s3_client, config.report_bucket_name, combined)
    history_key = write_history(s3_client, config.report_bucket_name, combined)

    s3_path = f"s3://{config.report_bucket_name}/{SUMMARY_KEY}"
    history_s3_path = f"s3://{config.report_bucket_name}/{history_key}"

    logger.info(
        "Cost explorer summary written s3_path=%s history_s3_path=%s",
        s3_path,
        history_s3_path,
    )
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "summary": combined,
                "history_s3_path": history_s3_path,
                "s3_path": s3_path,
            }
        ),
    }


def lambda_handler(event, context):
    try:
        return handle_event(event, context)
    except Exception as exc:
        error_msg = f"Cost explorer Lambda failed: {exc}"
        logger.exception(error_msg)
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}
if __name__ == "__main__":
    result = lambda_handler({}, None)
    if result.get("statusCode") != 200:
        sys.exit(1)
