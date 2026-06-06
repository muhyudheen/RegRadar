from celery import Celery
import os

celery_app = Celery(
    "regradar",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    include=[
        "app.workers.scraper_tasks",   # ← explicit include
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
        "run-all-scrapers": {
            "task": "scraper.run_all",
            "schedule": 900.0,          # 900 seconds = 15 minutes
        },
    },  
)

celery_app.autodiscover_tasks(["app.workers"])