"""
MIBSP Task Utilities
Synchronous task helpers used when Celery/Redis are not configured.
"""
import logging
import smtplib
from email.message import EmailMessage

from flask import current_app, has_app_context

from app.models import Complaint, User

logger = logging.getLogger(__name__)


def _collect_status_update_recipients(complaint):
    """Collect recipient emails for staff notifications."""
    recipients = set()

    if complaint and complaint.assigned_officer and complaint.assigned_officer.email:
        recipients.add(complaint.assigned_officer.email.strip())

    admins = User.query.filter_by(role='admin', is_active=True).all()
    for admin in admins:
        if admin.email:
            recipients.add(admin.email.strip())

    fallback = (current_app.config.get('NOTIFICATION_TO_EMAIL') or '').strip()
    if fallback:
        recipients.add(fallback)

    return sorted(email for email in recipients if email)


def send_system_email(subject, body, recipients):
    """Send SMTP email if mail settings are configured."""
    mail_server = (current_app.config.get('MAIL_SERVER') or '').strip()
    mail_port = int(current_app.config.get('MAIL_PORT', 587))
    mail_use_tls = bool(current_app.config.get('MAIL_USE_TLS', True))
    mail_username = (current_app.config.get('MAIL_USERNAME') or '').strip()
    mail_password = current_app.config.get('MAIL_PASSWORD') or ''

    if not mail_server:
        return False, 'MAIL_SERVER not configured.'
    if not recipients:
        return False, 'No recipients available.'

    sender = mail_username or 'no-reply@mibsp.local'

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = ', '.join(recipients)
    message.set_content(body)

    try:
        with smtplib.SMTP(mail_server, mail_port, timeout=15) as smtp:
            smtp.ehlo()
            if mail_use_tls:
                smtp.starttls()
                smtp.ehlo()
            if mail_username and mail_password:
                smtp.login(mail_username, mail_password)
            smtp.send_message(message)
        return True, None
    except Exception as exc:
        logger.exception('Email notification failed.')
        return False, str(exc)


def send_status_update_notification(tracking_id, new_status, contact_method=None):
    """
    Send status-update notifications to staff emails when configured.
    Falls back to structured logging if email settings are unavailable.
    """
    if not has_app_context():
        logger.info(
            '[TASK] Notification skipped (no app context): complaint=%s status=%s',
            tracking_id, new_status
        )
        return {
            'success': False,
            'tracking_id': tracking_id,
            'status': new_status,
            'mode': 'skipped'
        }

    complaint = Complaint.query.filter_by(tracking_id=tracking_id).first()
    recipients = _collect_status_update_recipients(complaint)

    subject = f'MIBSP Update: Complaint {tracking_id} is now {new_status}'
    body = (
        f'Complaint Tracking ID: {tracking_id}\n'
        f'New Status: {new_status}\n'
        f'Department: {complaint.department.name if complaint and complaint.department else "N/A"}\n'
        f'Service: {complaint.service.name if complaint and complaint.service else "N/A"}\n'
    )

    sent, error = send_system_email(subject, body, recipients)
    if sent:
        logger.info(
            '[TASK] Email notification sent: complaint=%s status=%s recipients=%s',
            tracking_id, new_status, len(recipients)
        )
        return {
            'success': True,
            'tracking_id': tracking_id,
            'status': new_status,
            'mode': 'email',
            'recipient_count': len(recipients)
        }

    logger.info(
        '[TASK] Notification fallback: complaint=%s status=%s reason=%s',
        tracking_id, new_status, error
    )
    return {
        'success': True,
        'tracking_id': tracking_id,
        'status': new_status,
        'mode': 'log',
        'reason': error
    }


def generate_daily_report():
    """Placeholder daily report hook for scheduler integration."""
    logger.info('[TASK] Daily report generation is not scheduled in this runtime.')
    return {}


def cleanup_old_uploads(days=30):
    """Placeholder upload cleanup hook for scheduler integration."""
    logger.info('[TASK] Upload cleanup is not scheduled in this runtime.')
    return {}


def backup_database():
    """Placeholder database backup hook for scheduler integration."""
    logger.info('[TASK] Database backup is not scheduled in this runtime.')
    return {}
