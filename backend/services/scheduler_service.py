"""
Scheduler Service
Auto-close overdue events with a fixed profit margin (no more daily reminders).

Previously this module sent daily WhatsApp reminders for every overdue event
until the admin closed it manually. That loop was replaced by automatic
closing (see services/auto_close_service.py): events are closed with a 70%
margin AUTO_CLOSE_DAYS after their date, and the admin is only alerted (once)
about events that cannot be closed automatically.
"""
import logging

from services.auto_close_service import auto_close_overdue_events

logger = logging.getLogger(__name__)


async def check_overdue_events() -> dict:
    """Entry point called by Cloud Scheduler: auto-close overdue events."""
    logger.info("🔍 Starting overdue events auto-close...")
    return await auto_close_overdue_events()


async def manual_check_overdue_events(force: bool = False) -> dict:
    """Manually trigger the auto-close (for testing). `force` kept for API compat."""
    logger.info("🔧 Manual auto-close triggered")
    return await auto_close_overdue_events()
