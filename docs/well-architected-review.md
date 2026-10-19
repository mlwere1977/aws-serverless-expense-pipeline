# Well-Architected self-review

Each pillar has a strength and an honest weakness. Replace the placeholders marked MEASURE with numbers from your own deployment before you submit, and rewrite the prose in your own words.

## Security

**Strength.** Each Lambda has its own inline IAM policy limited to the exact actions it needs: ingest can only `dynamodb:PutItem`, list can only `dynamodb:Scan`, and the processor can only `sns:Publish` and `sqs:SendMessage`, each on a single resource ARN. The API requires an API key. DynamoDB and SQS encrypt data at rest. Input is validated before anything is written, and 500 responses never leak internal error text (covered by a unit test). No credentials or personal values are committed to the repo; the name and email are deployment parameters.

**Weakness.** The API key is one shared secret, not a per-user identity, so there is no audit trail of who submitted what. A production version would use Cognito or IAM authorisation. The SNS topic is also not encrypted with a KMS key: the AWS-managed `aws/sns` key prevents CloudWatch alarms from publishing to the topic, and a customer-managed key adds cost and policy work.

## Reliability

**Strength.** Every service used is managed and multi-AZ. The stream consumer retries twice, bisects a failing batch to isolate a bad record, and then sends the failure to a dead-letter queue. Alarms on Lambda errors and on the DLQ turn silent failures into emails. Writes use a conditional put so an ID can never be overwritten, and DynamoDB point-in-time recovery is on.

**Weakness.** There is no client idempotency key, so a client that retries a timed-out POST can create a duplicate expense. The list endpoint reads at most 100 items with no pagination, and everything runs in a single region with no failover.

## Performance

**Strength.** All three functions do small, short work on arm64. DynamoDB on-demand scales with traffic, and alerting runs asynchronously through the stream, so a slow email never slows the API response.

**Weakness.** The list endpoint uses a Scan, which gets slower as the table grows, and Lambda cold starts add latency after idle periods. MEASURE: record the `Duration` and `Init Duration` values from the REPORT lines in the CloudWatch logs for a cold and a warm request, and state them here. Memory was left at 128 MB without tuning.

## Cost

**Strength.** Every component is pay-per-use, so idle cost is close to zero. The usage plan caps the API at 1,000 requests per month and throttles bursts, so a leaked key cannot create a large bill. Log retention is 14 days, and arm64 is the cheaper Lambda architecture. MEASURE: after a day of testing, check Billing and Cost Explorer and write the actual figure, plus a monthly estimate using the current AWS pricing pages.

**Weakness.** Point-in-time recovery, the CloudWatch alarms, and log storage are small but non-zero charges even when nothing is happening, and the template does not create an AWS Budget (set one by hand before deploying, as the guide describes). The Scan will cost more read capacity as the table grows.

## What I would change with more time

1. Replace the shared API key with Cognito authentication.
2. Add a global secondary index on `date` and switch the list endpoint from Scan to Query with pagination.
3. Accept a client idempotency key to remove duplicates on retry.
4. Encrypt the SNS topic with a customer-managed KMS key and update its key policy for CloudWatch.
