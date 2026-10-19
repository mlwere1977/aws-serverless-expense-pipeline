import json

from conftest import load_module

ingest = load_module("ingest_app", "src/ingest/app.py")
processor = load_module("processor_app", "src/processor/app.py")
lister = load_module("list_app", "src/list_expenses/app.py")


class FakeTable:
    def __init__(self, items=None):
        self.items = items or []

    def put_item(self, **kwargs):
        self.items.append(kwargs["Item"])

    def scan(self, **kwargs):
        return {"Items": list(self.items)}


def api_event(payload):
    return {"body": json.dumps(payload)}


def test_ingest_saves_valid_expense(monkeypatch):
    table = FakeTable()
    monkeypatch.setattr(ingest, "get_table", lambda: table)
    result = ingest.lambda_handler(api_event({"message": "I spent $45 on office supplies yesterday"}), None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 201
    assert body["submitted_by"] == "Test Student"
    assert len(table.items) == 1 and table.items[0]["status"] == "logged"


def test_ingest_missing_date_writes_nothing(monkeypatch):
    table = FakeTable()
    monkeypatch.setattr(ingest, "get_table", lambda: table)
    result = ingest.lambda_handler(api_event({"message": "Log $30 for lunch"}), None)
    assert result["statusCode"] == 400
    assert json.loads(result["body"])["missing_fields"] == ["date"]
    assert table.items == []


def test_ingest_rejects_bad_json(monkeypatch):
    monkeypatch.setattr(ingest, "get_table", lambda: FakeTable())
    assert ingest.lambda_handler({"body": "{nope"}, None)["statusCode"] == 400
    assert ingest.lambda_handler({"body": "[1,2]"}, None)["statusCode"] == 400


def test_ingest_hides_internal_errors(monkeypatch):
    class Boom:
        def put_item(self, **kwargs):
            raise RuntimeError("secret internal detail")

    monkeypatch.setattr(ingest, "get_table", lambda: Boom())
    result = ingest.lambda_handler(api_event({"expense": "X", "amount": 5, "date": "2026-01-01"}), None)
    assert result["statusCode"] == 500
    assert "secret" not in result["body"]


class FakeSns:
    def __init__(self):
        self.published = []

    def publish(self, **kwargs):
        self.published.append(kwargs)


def stream_record(amount, event_name="INSERT"):
    return {
        "eventName": event_name,
        "dynamodb": {
            "NewImage": {
                "expense_id": {"S": "abc"},
                "expense": {"S": "Laptop dock"},
                "amount": {"N": str(amount)},
                "category": {"S": "Office"},
                "date": {"S": "2026-10-01"},
            }
        },
    }


def test_processor_alerts_only_for_large_expenses(monkeypatch):
    sns = FakeSns()
    monkeypatch.setattr(processor, "get_sns", lambda: sns)
    monkeypatch.setenv("REVIEW_THRESHOLD", "500")
    monkeypatch.setenv("TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:t")
    result = processor.lambda_handler({"Records": [stream_record(45), stream_record(650)]}, None)
    assert result["alerts_sent"] == 1
    assert "650" in sns.published[0]["Subject"]
    assert "Test Student" in sns.published[0]["Message"]


def test_processor_ignores_non_insert(monkeypatch):
    sns = FakeSns()
    monkeypatch.setattr(processor, "get_sns", lambda: sns)
    monkeypatch.setenv("REVIEW_THRESHOLD", "500")
    monkeypatch.setenv("TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:t")
    processor.lambda_handler({"Records": [stream_record(900, "MODIFY")]}, None)
    assert sns.published == []


def test_list_sorts_newest_first(monkeypatch):
    from decimal import Decimal

    items = [
        {"expense": "old", "date": "2026-09-01", "created_at": "a", "amount": Decimal("1")},
        {"expense": "new", "date": "2026-10-01", "created_at": "b", "amount": Decimal("2.5")},
    ]
    monkeypatch.setattr(lister, "get_table", lambda: FakeTable(items))
    body = json.loads(lister.lambda_handler({}, None)["body"])
    assert [e["expense"] for e in body["expenses"]] == ["new", "old"]
    assert body["submitted_by"] == "Test Student"
