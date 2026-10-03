"""Celery application (plan §4.3, ordered.md 7.2).

Docker (Linux):   celery -A talentgraph.worker.celery_app worker -Q parse,webhooks -l info
Windows (native): uv run celery -A talentgraph.worker.celery_app worker --pool=solo -l info
"""

from typing import Any

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from talentgraph.config import get_settings

settings = get_settings()

celery_app = Celery(
    "talentgraph",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["talentgraph.worker.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=60,
    task_time_limit=90,
    task_default_queue="parse",
    task_routes={"talentgraph.deliver_webhook": {"queue": "webhooks"}},
    worker_concurrency=settings.celery_concurrency,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
)

app = celery_app  # `celery -A talentgraph.worker.celery_app` finds `app`/`celery_app`


@worker_process_init.connect  # type: ignore[untyped-decorator]
def _init_process(**_: Any) -> None:
    """Per-process setup: logging now; DB engine, Encoder and AgentRegistry from Phase 5.6."""
    from talentgraph.observability.logging import configure_logging

    configure_logging(settings.log_level)


@worker_process_shutdown.connect  # type: ignore[untyped-decorator]
def _shutdown_process(**_: Any) -> None:
    """Phase 5.6: registry.shutdown() and engine disposal."""
