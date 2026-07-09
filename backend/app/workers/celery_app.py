from celery import Celery
import os

celery_app = Celery(
    "lawhook",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    include=[
        "app.workers.scraper_tasks",
        "app.workers.ai_tasks",
        "app.workers.webhook_tasks",
        "app.workers.scheduler",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Beat schedule — scraper runs every 15 minutes
    beat_schedule={# Run all scrapers every 15 minutes
        "demand-driven-scheduler-tick": {
            "task": "scheduler.tick",
            "schedule": 900.0,          # 900 seconds = 15 minutes
        },
    },  
)
