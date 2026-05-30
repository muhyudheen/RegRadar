from celery import Celery
import os

celery_app = Celery(
    "regradar",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Beat schedule — scraper runs every 15 minutes
    beat_schedule={},  # Empty for now — add tasks here later
)