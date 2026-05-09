from celery import Celery
import os

celery_app = Celery(
    "carmates",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=["tasks"]  # ← ADD THIS
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Australia/Sydney",
    enable_utc=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,  # ← ADD THIS (fixes warning)
)
