"""
MIBSP Notification Stubs
Celery removed for local dev — these are plain function stubs.
Ready to be upgraded to real Celery tasks when Redis is available.
"""
import logging

logger = logging.getLogger(__name__)


def send_status_update_notification(tracking_id, new_status, contact_method=None):
    """
    Stub: Send notification when complaint status changes.
    Plug in Twilio / SendGrid / Firebase here when ready.
    """
    logger.info(f'[STUB] Notification: complaint {tracking_id} → {new_status}')
    return {'success': True, 'tracking_id': tracking_id, 'status': new_status}


def generate_daily_report():
    """Stub: Generate daily analytics report."""
    logger.info('[STUB] Daily report generation skipped (no Celery).')
    return {}


def cleanup_old_uploads(days=30):
    """Stub: Clean up old uploaded files."""
    logger.info('[STUB] Upload cleanup skipped (no Celery).')
    return {}


def backup_database():
    """Stub: Trigger database backup."""
    logger.info('[STUB] DB backup skipped (no Celery).')
    return {}
