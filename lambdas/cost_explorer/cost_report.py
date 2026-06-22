try:
    from .report import extract_amount, generate_cost_report
except ImportError:
    from report import extract_amount, generate_cost_report
