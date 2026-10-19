from datetime import date
from decimal import Decimal

from expense_parser import build_expense, infer_category, parse_message

TODAY = date(2026, 10, 4)


def test_parses_the_original_n8n_example():
    result = parse_message("I spent $45 on office supplies yesterday.", TODAY)
    assert result == {
        "expense": "Office supplies",
        "amount": "45",
        "category": "Office",
        "date": "2026-10-03",
    }


def test_missing_date_is_reported_not_guessed():
    item, errors, missing = build_expense({"message": "Log $30 for lunch"}, TODAY)
    assert item is None
    assert missing == ["date"]


def test_complete_message_builds_item():
    item, errors, missing = build_expense({"message": "I paid $100 for groceries today"}, TODAY)
    assert (errors, missing) == ([], [])
    assert item["amount"] == Decimal("100.00")
    assert item["category"] == "Food"
    assert item["date"] == "2026-10-04"


def test_structured_fields_override_message():
    body = {"message": "I spent $10 on coffee today", "amount": 12.5}
    item, _, _ = build_expense(body, TODAY)
    assert item["amount"] == Decimal("12.50")


def test_explicit_iso_date_in_message():
    item, _, _ = build_expense({"message": "Paid $20 for taxi on 2026-09-30"}, TODAY)
    assert item["expense"] == "Taxi"
    assert item["date"] == "2026-09-30"


def test_rejects_negative_zero_and_huge_amounts():
    for bad in (-5, 0, 100001, "abc", "NaN"):
        item, errors, _ = build_expense({"expense": "X", "amount": bad, "date": "2026-10-01"}, TODAY)
        assert item is None and errors, bad


def test_rejects_future_and_malformed_dates():
    for bad in ("2026-10-05", "10/01/2026", "not-a-date"):
        item, errors, _ = build_expense({"expense": "X", "amount": 5, "date": bad}, TODAY)
        assert item is None and errors, bad


def test_rejects_unknown_category():
    item, errors, _ = build_expense(
        {"expense": "X", "amount": 5, "date": "2026-10-01", "category": "Yachts"}, TODAY
    )
    assert item is None and errors


def test_category_is_normalised():
    item, _, _ = build_expense(
        {"expense": "X", "amount": 5, "date": "2026-10-01", "category": "travel"}, TODAY
    )
    assert item["category"] == "Travel"


def test_infer_category_defaults_to_other():
    assert infer_category("unicycle repair") == "Other"
    assert infer_category("team dinner") == "Food"
