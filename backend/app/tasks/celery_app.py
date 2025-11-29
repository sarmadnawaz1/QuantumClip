"""Celery application configuration."""

from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "shazi_videogen",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.video_generation"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_time_limit - 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=10,
)

if __name__ == "__main__":
    celery_app.start()

