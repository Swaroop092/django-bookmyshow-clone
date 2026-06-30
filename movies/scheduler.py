from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

def release_expired_locks():
    try:
        from .models import Seat
        # Release locks older than 2 minutes
        expiration_time = timezone.now() - timedelta(minutes=2)
        expired_seats = Seat.objects.filter(locked_at__lt=expiration_time, is_booked=False, locked_by__isnull=False)
        count = expired_seats.count()
        if count > 0:
            expired_seats.update(locked_by=None, locked_at=None)
            logger.info(f"Released {count} expired seat locks.")
    except Exception as e:
        logger.error(f"Error releasing locks: {e}")

def process_email_queue():
    try:
        from .models import EmailQueue
        from django.core.mail import send_mail
        from django.conf import settings
        from django.db.models import Q
        
        # Get tasks that are Pending, or Failed but with retries < 3
        tasks = EmailQueue.objects.filter(Q(status='Pending') | Q(status='Failed', retries__lt=3))
        
        for task in tasks:
            try:
                send_mail(
                    task.subject,
                    'Your booking is confirmed.', # plaintext fallback
                    settings.EMAIL_HOST_USER,
                    [task.recipient],
                    html_message=task.html_message,
                    fail_silently=False,
                )
                task.status = 'Sent'
                task.save()
                logger.info(f"Successfully sent email to {task.recipient}")
            except Exception as e:
                task.retries += 1
                task.status = 'Failed'
                task.save()
                logger.error(f"Failed to send email to {task.recipient}. Retry {task.retries}/3. Error: {e}")
                
    except Exception as e:
        logger.error(f"Error processing email queue: {e}")

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(release_expired_locks, 'interval', minutes=1)
    scheduler.add_job(process_email_queue, 'interval', minutes=1)
    scheduler.start()
