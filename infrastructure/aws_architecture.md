# AWS architecture notes

This MVP is intentionally simple and cloud-ready.

- FastAPI exposes the local operational API for analysis and incident management.
- Lambda can wrap the same risk logic for serverless deployment.
- Bedrock can be activated through the `AWS_AI_ENABLED` environment variable.
- S3, DynamoDB, and SNS are abstracted behind service classes and not required for local development.
- API Gateway can proxy the FastAPI endpoint or Lambda handler once deployed.
