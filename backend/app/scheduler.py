"""APScheduler singleton for the in-process background scheduler.

Usage:
    from app.scheduler import scheduler
    scheduler.start()   # in FastAPI lifespan on startup
    scheduler.shutdown()  # in FastAPI lifespan on teardown

The poll job is registered here and uses settings.imap_poll_interval_minutes.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    """Register the IMAP poll job and start the scheduler."""
    from app.worker import run_poll_cycle  # local import avoids circular deps

    interval_minutes = max(1, settings.imap_poll_interval_minutes)

    scheduler.add_job(
        run_poll_cycle,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="imap_poll",
        replace_existing=True,
        misfire_grace_time=60,
    )
    scheduler.start()
    logger.info("Scheduler started — IMAP poll every %d minute(s)", interval_minutes)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
