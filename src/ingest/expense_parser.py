"""Parsing and validation for expenses.

Pure Python with no AWS calls, so it is trivial to unit test. This replaces the
"system prompt" from the n8n agent: the same rules (extract fields, ask for
missing ones, never save bad data) are now explicit, testable code.
"""
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

ALLOWED_CATEGORIES = ["Office", "Food", "Travel", "Software", "Utilities", "Other"]

CATEGORY_KEYWORDS = {
    "Office": ["office", "supplies", "stationery", "printer", "paper", "desk", "monitor"],
    "Food": ["lunch", "dinner", "breakfast", "coffee", "groceries", "restaurant", "meal", "snacks"],
    "Travel": ["uber", "lyft", "flight", "hotel", "taxi", "gas", "parking", "train", "airfare"],
    "Software": ["subscription", "software", "license", "saas", "domain", "hosting"],
    "Utilities": ["electric", "internet", "phone", "water", "utility", "utilities"],
}

MAX_AMOUNT = Decimal("100000")
REQUIRED_FIELDS = ("expense", "amount", "date")

_AMOUNT_PATTERNS = [
    re.compile(r"\$\s*(\d[\d,]*(?:\.\d{1,2})?)"),
    re.compile(r"(\d[\d,]*(?:\.\d{1,2})?)\s*(?:dollars|usd|bucks)\b", re.IGNORECASE),
]
_ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_DESCRIPTION = re.compile(
    r"\b(?:on|for)\s+(?!\d{4}-\d{2}-\d{2})(.+?)"
    r"(?:\s+(?:yesterday|today)\b|\s+on\s+\d{4}-\d{2}-\d{2}|\s*[.!?]*\s*$)",
    re.IGNORECASE,
)


def infer_category(description):
    words = set(re.findall(r"[a-z]+", (description or "").lower()))
    for category, keywords in CATEGORY_KEYWORDS.items():
        if words & set(keywords):
            return category
    return "Other"


def resolve_date(text, today):
    """Return an ISO date string found in free text, or None."""
    match = _ISO_DATE.search(text)
    if match:
        return match.group(1)
    lowered = text.lower()
    if re.search(r"\byesterday\b", lowered):
        return (today - timedelta(days=1)).isoformat()
    if re.search(r"\btoday\b", lowered):
        return today.isoformat()
    return None


def parse_message(message, today):
    """Pull expense, amount, category and date out of a plain-English sentence.

    Any field that cannot be found is returned as None so the caller can ask for it.
    """
    amount = None
    for pattern in _AMOUNT_PATTERNS:
        found = pattern.search(message)
        if found:
            amount = found.group(1).replace(",", "")
            break

    description = None
    found = _DESCRIPTION.search(message)
    if found:
        description = found.group(1).strip()
        if description:
            description = description[0].upper() + description[1:]

    return {
        "expense": description,
        "amount": amount,
        "category": infer_category(description) if description else None,
        "date": resolve_date(message, today),
    }


def build_expense(body, today):
    """Validate a request body.

    Returns (item, errors, missing). `item` is only set when both lists are empty.
    A body may carry a free-text "message", structured fields, or both
    (structured fields win).
    """
    message = body.get("message")
    parsed = parse_message(message, today) if isinstance(message, str) else {}
    fields = {key: body.get(key, parsed.get(key)) for key in ("expense", "amount", "date", "category")}

    if fields["category"] in (None, "") and fields["expense"]:
        fields["category"] = infer_category(str(fields["expense"]))

    missing = [key for key in REQUIRED_FIELDS if fields[key] in (None, "")]
    errors = []
    expense = amount = day = category = None

    if "expense" not in missing:
        expense = str(fields["expense"]).strip()
        if not expense or len(expense) > 100:
            errors.append("expense must be 1 to 100 characters")

    if "amount" not in missing:
        try:
            amount = Decimal(str(fields["amount"]))
        except InvalidOperation:
            errors.append("amount must be a number")
        else:
            if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
                errors.append("amount must be greater than 0 and at most 100000")
            else:
                amount = amount.quantize(Decimal("0.01"))

    if "date" not in missing:
        try:
            day = date.fromisoformat(str(fields["date"]))
        except ValueError:
            errors.append("date must look like YYYY-MM-DD")
        else:
            if day > today:
                errors.append("date cannot be in the future")

    category = str(fields["category"] or "Other").strip().title()
    if category not in ALLOWED_CATEGORIES:
        errors.append("category must be one of: " + ", ".join(ALLOWED_CATEGORIES))

    if missing or errors:
        return None, errors, missing

    return {
        "expense": expense,
        "amount": amount,
        "category": category,
        "date": day.isoformat(),
    }, [], []
