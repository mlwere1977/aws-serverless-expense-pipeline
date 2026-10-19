#!/usr/bin/env bash
# End-to-end check of the deployed pipeline. Produces the output you screenshot.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/get_config.sh"
echo

post() {
  curl -sS -w "\nHTTP %{http_code}\n" -X POST "$API_URL" \
    -H "x-api-key: $API_KEY" -H "Content-Type: application/json" -d "$1"
  echo
}

TODAY="$(date -u +%F)"

echo "== 1. Plain-English message with complete information (expect 201) =="
post '{"message": "I spent $45 on office supplies yesterday."}'

echo "== 2. Missing date (expect 400, nothing saved) =="
post '{"message": "Log $30 for lunch"}'

echo "== 3. Large expense (expect 201, then a 'needs review' email) =="
post "{\"expense\": \"Laptop dock\", \"amount\": 650, \"category\": \"Office\", \"date\": \"$TODAY\"}"

echo "== 4. Invalid amount (expect 400) =="
post "{\"expense\": \"Bad entry\", \"amount\": -5, \"date\": \"$TODAY\"}"

echo "== 5. No API key (expect 403) =="
curl -sS -w "\nHTTP %{http_code}\n" -X POST "$API_URL" -H "Content-Type: application/json" \
  -d '{"message": "I spent $5 on coffee today"}'
echo

echo "== 6. List stored expenses (expect 2 items: office supplies and laptop dock) =="
curl -sS -w "\nHTTP %{http_code}\n" "$API_URL" -H "x-api-key: $API_KEY"
