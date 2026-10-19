# Design decisions

For every major choice: what was chosen, the alternative that was rejected, and why. These are starting drafts. Rewrite them in your own words and adjust anything you disagree with before using them in your report, because you are the one who has to defend them.

| Decision | Chosen | Rejected alternative | Why |
|---|---|---|---|
| Project shape | Serverless event-driven pipeline | ECS/Fargate microservices | Traffic is tiny and bursty. Serverless costs nothing at idle and has no servers or cluster to patch. |
| Compute | Three small Lambda functions | One Lambda doing everything; EC2 | One function per job allows least-privilege IAM per job and separate scaling and logs. EC2 would be billed while idle. |
| API front door | API Gateway REST API with API key and usage plan | HTTP API; Lambda function URL | REST API supports API keys, usage plans, and quotas natively, which gives a cost cap and a simple access control. HTTP API is cheaper but has no usage plans. Function URLs have no throttling or quota. |
| Database | DynamoDB on-demand | RDS/Aurora; S3 files | Access is key-based writes and small reads, with no joins. On-demand has no idle cost and no capacity planning. RDS bills hourly even when idle. |
| Eventing | DynamoDB Streams to Lambda | Ingest Lambda publishing to SNS/EventBridge directly | The stream fires only after the write is durable, so an alert can never describe an expense that was not saved. It also decouples alerting from API latency. |
| Notification | SNS email | SES; Slack webhook | SNS needs no domain verification and supports email subscriptions in minutes. SES requires verified identities and sandbox exit for arbitrary recipients. |
| Failure handling | Retries, bisect, SQS dead-letter queue, alarms | Silent drop; unlimited retries | Bounded retries stop a poison record from blocking the stream. The DLQ preserves evidence and the alarm makes failures visible. |
| Input handling | Deterministic regex parser and validator | Calling an LLM (Bedrock/OpenAI) per request | Free, instant, testable, and has no extra service or secret. The trade-off is that unusual phrasing needs a structured request. |
| Infrastructure as code | CloudFormation (SAM transform) | Terraform; console clicking | The course allows either. CloudFormation needs no extra tooling in CloudShell and `aws cloudformation deploy` is a single command. |
| Observability | CloudWatch logs (14-day retention) and three alarms | No alarms; third-party tooling | Alarms are free-tier eligible, and retention limits log storage cost. |
| Architecture | arm64, 128 MB Lambdas | x86_64, larger memory | arm64 is cheaper per millisecond. The functions do trivial work, so 128 MB is enough; measure before raising it. |

## Behaviour carried over from the n8n agent

| n8n agent (Module 10) | This project |
|---|---|
| System prompt: extract expense, amount, category, date | `expense_parser.py` |
| Ask for the missing date | HTTP 400 with `missing_fields: ["date"]` |
| Never save without confirmation or when declined | Invalid input is rejected and nothing is written |
| Google Sheet as the store | DynamoDB table |
| Status column | `status` attribute (`logged`) |
