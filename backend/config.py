import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


class Settings:
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_PROFILE = os.getenv("AWS_PROFILE", "")
    AWS_AI_ENABLED = os.getenv("AWS_AI_ENABLED", "false").lower() == "true"
    AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "")
    AWS_DYNAMODB_ENABLED = os.getenv("AWS_DYNAMODB_ENABLED", "false").lower() == "true"
    AWS_DYNAMODB_TABLE = os.getenv("AWS_DYNAMODB_TABLE", "EcoOpsIncidents")
    AWS_SNS_ENABLED = os.getenv("AWS_SNS_ENABLED", "false").lower() == "true"
    AWS_SNS_TOPIC_ARN = os.getenv("AWS_SNS_TOPIC_ARN", "")
    AWS_BEDROCK_MODEL_ID = os.getenv("AWS_BEDROCK_MODEL_ID", "")


settings = Settings()
