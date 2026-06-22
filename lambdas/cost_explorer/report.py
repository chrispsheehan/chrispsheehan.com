from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

try:
    from .config import CostExplorerConfig
except ImportError:
    from config import CostExplorerConfig

logger = logging.getLogger(__name__)


def extract_amount(result_by_time, preferred_order=("UnblendedCost", "BlendedCost")) -> float:
    for metric in preferred_order:
        amount_str = result_by_time["Total"].get(metric, {}).get("Amount")
        if amount_str and float(amount_str) > 0:
            return float(amount_str)
    return 0.0


def generate_cost_report(
    config: CostExplorerConfig,
    *,
    cost_explorer_client: Any,
    today=None,
) -> dict[str, Any]:
    metrics = ["UnblendedCost"]
    today = today or datetime.now(timezone.utc).date()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)

    cost_filter = {
        "And": [
            {
                "Tags": {
                    "Key": "Environment",
                    "Values": [config.environment_name],
                    "MatchOptions": ["EQUALS"],
                }
            },
            {
                "Tags": {
                    "Key": "Project",
                    "Values": [config.project_name],
                    "MatchOptions": ["EQUALS"],
                }
            },
        ]
    }

    prev_month_resp = cost_explorer_client.get_cost_and_usage(
        TimePeriod={
            "Start": str(first_day_prev_month),
            "End": str(last_day_prev_month + timedelta(days=1)),
        },
        Granularity="MONTHLY",
        Metrics=metrics,
        Filter=cost_filter,
    )

    last_month_total = extract_amount(prev_month_resp["ResultsByTime"][0])
    billing_month = first_day_prev_month.strftime("%Y-%m")

    result = {
        "billing-month": billing_month,
        "last-month-total": round(last_month_total, 2),
        "generated-at": str(today),
    }

    logger.info("Cost explorer summary generated billing_month=%s total=%s", billing_month, result["last-month-total"])
    return result
