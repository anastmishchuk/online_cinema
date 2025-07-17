from celery import Celery
import os

from celery.schedules import crontab

celery_app = Celery(
    "online_cinema",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

celery_app.autodiscover_tasks(["src.users.tasks"])

celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens-every-hour": {
        "task": "src.users.tasks.cleanup_expired_tokens",
        "schedule": crontab(minute=0, hour="*"),
    },
}
