#!/usr/bin/env bash
# Package the Lambda code, upload it to S3, and deploy template.yaml with CloudFormation.
# Usage:
#   export STUDENT_NAME="Your Name"
#   export ALERT_EMAIL="you@example.com"
#   ./deploy.sh
set -euo pipefail

STACK="${STACK_NAME:-expense-pipeline}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(aws configure get region || true)}}"
REGION="${REGION:-us-east-1}"
: "${STUDENT_NAME:?Set STUDENT_NAME, e.g. export STUDENT_NAME=\"Your Name\"}"
: "${ALERT_EMAIL:?Set ALERT_EMAIL, e.g. export ALERT_EMAIL=you@example.com}"
THRESHOLD="${REVIEW_THRESHOLD:-500}"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${STACK}-artifacts-${ACCOUNT}-${REGION}"

echo "==> Region: $REGION | Stack: $STACK | Artifact bucket: $BUCKET"

if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "==> Creating artifact bucket"
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
      --create-bucket-configuration LocationConstraint="$REGION" >/dev/null
  fi
  aws s3api put-public-access-block --bucket "$BUCKET" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
fi

echo "==> Packaging"
aws cloudformation package \
  --template-file template.yaml \
  --s3-bucket "$BUCKET" \
  --output-template-file packaged.yaml \
  --region "$REGION" >/dev/null

echo "==> Deploying (2-4 minutes)"
aws cloudformation deploy \
  --template-file packaged.yaml \
  --stack-name "$STACK" \
  --capabilities CAPABILITY_IAM \
  --region "$REGION" \
  --parameter-overrides \
    "StudentName=${STUDENT_NAME}" \
    "AlertEmail=${ALERT_EMAIL}" \
    "ReviewThreshold=${THRESHOLD}"

echo
echo "==> Stack outputs"
aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table

echo
echo "NEXT: open the 'AWS Notification - Subscription Confirmation' email and click Confirm subscription."
echo "THEN: ./scripts/smoke_test.sh"
