#!/usr/bin/env bash
# Source this file to export API_URL and API_KEY for the deployed stack:
#   source scripts/get_config.sh
STACK="${STACK_NAME:-expense-pipeline}"

API_URL="$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)"
API_ID="$(aws cloudformation describe-stack-resource --stack-name "$STACK" \
  --logical-resource-id ExpenseApi --query StackResourceDetail.PhysicalResourceId --output text)"
API_KEY="$(aws apigateway get-api-keys --include-values \
  --query "items[?contains(stageKeys, '${API_ID}/prod')].value | [0]" --output text)"

export API_URL API_KEY
echo "API_URL=$API_URL"
echo "API_KEY=(loaded, ${#API_KEY} characters)"
