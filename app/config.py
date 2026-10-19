import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kvitto.db")
DEFAULT_WEBHOOK_SECRET = "kvitto-demo-webhook-secret"


def get_webhook_secret() -> str:
    return os.getenv("WEBHOOK_SECRET", DEFAULT_WEBHOOK_SECRET)
