"""Celery tasks. `parse_item`, `finalize_batch` and `deliver_webhook` are implemented in Phase 7."""

from talentgraph.worker.celery_app import celery_app


@celery_app.task(name="talentgraph.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    """Smoke-test task for Phase 0 exit criterion 0-I."""
    return "pong"
