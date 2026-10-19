"""DynamoDB Streams consumer: email an alert when a new expense is large.

Triggered only for INSERT events (filtered in the event source mapping). If this
function raises, Lambda retries the batch, bisects it, and finally sends the
failure record to the SQS dead-letter queue, which raises a CloudWatch alarm.
"""
import json
import logging
import os
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_sns = None


def get_sns():
    global _sns
    if _sns is None:
        import boto3

        _sns = boto3.client("sns")
    return _sns


def _deserialize(image):
    from boto3.dynamodb.types import TypeDeserializer

    deserializer = TypeDeserializer()
    return {key: deserializer.deserialize(value) for key, value in image.items()}


def lambda_handler(event, context):
    threshold = Decimal(os.environ["REVIEW_THRESHOLD"])
    topic_arn = os.environ["TOPIC_ARN"]
    student = os.environ.get("STUDENT_NAME", "unknown")
    alerts = 0

    for record in event.get("Records", []):
        if record.get("eventName") != "INSERT":
            continue
        item = _deserialize(record["dynamodb"]["NewImage"])
        amount = Decimal(str(item["amount"]))
        logger.info(
            json.dumps(
                {"event": "expense_processed", "expense_id": item.get("expense_id"), "amount": str(amount)}
            )
        )
        if amount >= threshold:
            get_sns().publish(
                TopicArn=topic_arn,
                Subject=f"Expense needs review: ${amount}",
                Message=(
                    f"An expense at or above ${threshold} was logged.\n\n"
                    f"Expense:   {item.get('expense')}\n"
                    f"Amount:    ${amount}\n"
                    f"Category:  {item.get('category')}\n"
                    f"Date:      {item.get('date')}\n"
                    f"ID:        {item.get('expense_id')}\n\n"
                    f"Pipeline owner: {student}"
                ),
            )
            alerts += 1

    return {"records": len(event.get("Records", [])), "alerts_sent": alerts}
