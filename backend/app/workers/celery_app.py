"""Celery application factory."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings


def make_celery() -> Celery:
    settings = get_settings()
    app = Celery(
        "casa_estimation",
        broker=settings.effective_celery_broker,
        backend=settings.effective_celery_backend,
        include=["app.workers.tasks"],
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_default_retry_delay=10,
        task_track_started=True,
        task_time_limit=600,         # hard 10-minute timeout
        task_soft_time_limit=540,    # soft 9-minute timeout
        broker_connection_retry_on_startup=True,
    )
    return app


celery_app = make_celery()
