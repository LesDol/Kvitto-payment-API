import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kvitto.db")


def get_webhook_secret() -> str:
    return os.getenv("WEBHOOK_SECRET", "")
