import logging
import threading

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import UserProfile

logger = logging.getLogger(__name__)


def _send_email_async(subject, message, from_email, recipient_list, html_message=None):
    """Send email in a background thread to avoid blocking the request."""

    def send():
        try:
            send_mail(
                subject,
                message,
                from_email,
                recipient_list,
                html_message=html_message,
            )
            logger.info(f"Email sent to {recipient_list}")
        except Exception as e:
            logger.error(f"Error sending email to {recipient_list}: {str(e)}")

    thread = threading.Thread(target=send, daemon=True)
    thread.start()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when a new user is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """Send welcome email asynchronously when a new user registers."""
    if created:
        logger.info(f"New user created: {instance.username}")
        subject = "Welcome to Nova VTU!"
        html_message = render_to_string("emails/welcome_email.html", {"user": instance})
        message = strip_tags(html_message)

        # Send email in background thread (non-blocking)
        _send_email_async(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            html_message=html_message,
        )
