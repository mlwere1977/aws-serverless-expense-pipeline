"""POST /expenses: parse, validate and store one expense.

Accepts either structured JSON ({"expense","amount","date","category"}) or a
plain-English {"message": "I spent $45 on office supplies yesterday."}.
Missing or invalid fields return HTTP 400 (the API equivalent of the n8n agent
asking a follow-up question) and nothing is written.
"""
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from expense_parser import build_expense

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_table = None


def get_table():
    """Create the DynamoDB handle lazily so unit tests need no AWS setup."""
    global _table
    if _table is None:
        import boto3

        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def _default(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Cannot serialise {type(value)}")


def response(status, payload):
    payload = dict(payload, submitted_by=os.environ.get("STUDENT_NAME", "unknown"))
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, default=_default),
    }


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except (TypeError, json.JSONDecodeError):
        return response(400, {"error": "Request body must be valid JSON"})
    if not isinstance(body, dict):
        return response(400, {"error": "Request body must be a JSON object"})

    today = datetime.now(timezone.utc).date()
    item, errors, missing = build_expense(body, today)
    if missing or errors:
        return response(
            400,
            {
                "error": "validation_failed",
                "missing_fields": missing,
                "errors": errors,
                "hint": 'Send {"message": "I spent $45 on office supplies yesterday"} '
                'or {"expense","amount","date","category"}.',
            },
        )

    item.update(
        {
            "expense_id": str(uuid.uuid4()),
            "status": "logged",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "submitted_by": os.environ.get("STUDENT_NAME", "unknown"),
        }
    )

    try:
        get_table().put_item(Item=item, ConditionExpression="attribute_not_exists(expense_id)")
    except Exception:
        logger.exception("DynamoDB write failed")
        return response(500, {"error": "Could not save the expense"})

    logger.info(json.dumps({"event": "expense_saved", "expense_id": item["expense_id"], "category": item["category"]}))
    return response(201, {"message": "Expense saved", "expense": item})
