# Serverless Expense Pipeline (AWS)

CS 79C final project: an event-driven expense tracker built entirely from AWS managed services and defined in CloudFormation. It is a rebuild of an earlier n8n "Expense Tracker Agent" lab, with the chat agent replaced by an API, explicit validation code, and an event-driven alerting path.

![Architecture](docs/architecture.png)

## What it does

1. A client sends `POST /expenses` with either plain English (`"I spent $45 on office supplies yesterday."`) or structured JSON.
2. **API Gateway** checks the API key and throttles traffic, then invokes the **ingest Lambda**.
3. The ingest Lambda extracts and validates the fields. Missing or invalid input returns HTTP 400 and nothing is saved (the same confirm-before-saving behaviour the n8n agent enforced with its system prompt).
4. Valid expenses are written to **DynamoDB**.
5. DynamoDB Streams invokes the **processor Lambda** for every new item. If the amount is at or above the review threshold (default $500) it publishes an **SNS** email alert.
6. If the processor keeps failing, the batch goes to an **SQS dead-letter queue**. **CloudWatch** alarms on Lambda errors and on the DLQ email you through the same SNS topic.

Every response includes `submitted_by` with your name, so the output proves it is your deployment.

## AWS services used

API Gateway, Lambda (x3), DynamoDB (with Streams), SNS, SQS, CloudWatch (Logs and Alarms), IAM, CloudFormation, S3 (deployment artifacts only).

## Repository layout

```
template.yaml            CloudFormation (SAM) template: every resource
src/ingest/              POST /expenses Lambda + expense_parser.py
src/list_expenses/       GET /expenses Lambda
src/processor/           DynamoDB Streams consumer that sends alerts
tests/                   17 unit tests (no AWS account needed)
deploy.sh                package + deploy with the AWS CLI
scripts/                 get_config.sh, smoke_test.sh, cleanup.sh
docs/                    architecture diagram, design decisions, Well-Architected review
.github/workflows/ci.yml runs pytest and cfn-lint on every push
```

## Deploy

Run these in AWS CloudShell (or any shell with the AWS CLI configured):

```bash
git clone https://github.com/<your-username>/aws-serverless-expense-pipeline.git
cd aws-serverless-expense-pipeline
export STUDENT_NAME="Your Name"
export ALERT_EMAIL="you@example.com"
./deploy.sh
```

Then click **Confirm subscription** in the email from AWS Notifications and run:

```bash
./scripts/smoke_test.sh
```

## Try it manually

```bash
source scripts/get_config.sh
curl -X POST "$API_URL" -H "x-api-key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"message": "I spent $45 on office supplies yesterday."}'
curl "$API_URL" -H "x-api-key: $API_KEY"
```

## Run the tests locally

```bash
pip install -r requirements-dev.txt
pytest -q
cfn-lint template.yaml
```

## Cost

Everything is pay-per-use, and the usage plan caps the API at 1,000 requests per month. Typical project usage costs well under a dollar; log retention is 14 days. See `docs/well-architected-review.md` for the full cost reasoning, and run `./scripts/cleanup.sh` to delete everything.

## Documentation

- [Design decisions and rejected alternatives](docs/design-decisions.md)
- [Well-Architected self-review](docs/well-architected-review.md)
