"""GET /expenses: return the most recent expenses, newest first.

Uses a bounded Scan. That is fine for a few hundred items; the design notes
explain what to change (a GSI plus Query) if the table grew.
"""
import json
import os
from decimal import Decimal

_table = None
MAX_ITEMS = 100


def get_table():
    global _table
    if _table is None:
        import boto3

        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def _default(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Cannot serialise {type(value)}")


def lambda_handler(event, context):
    items = get_table().scan(Limit=MAX_ITEMS).get("Items", [])
    items.sort(key=lambda i: (i.get("date", ""), i.get("created_at", "")), reverse=True)
    body = {
        "count": len(items),
        "expenses": items,
        "submitted_by": os.environ.get("STUDENT_NAME", "unknown"),
    }
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=_default),
    }
