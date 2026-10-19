#!/usr/bin/env bash
# Delete everything this project created (stack + artifact bucket).
set -euo pipefail
STACK="${STACK_NAME:-expense-pipeline}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(aws configure get region || true)}}"
REGION="${REGION:-us-east-1}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${STACK}-artifacts-${ACCOUNT}-${REGION}"

echo "==> Deleting stack $STACK"
aws cloudformation delete-stack --stack-name "$STACK" --region "$REGION"
aws cloudformation wait stack-delete-complete --stack-name "$STACK" --region "$REGION"

echo "==> Removing artifact bucket $BUCKET"
aws s3 rb "s3://$BUCKET" --force --region "$REGION" || true
echo "Done. Nothing from this project should still be billing."
