from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.models import User

# @receiver(post_save, sender=User)
# def send_welcome_email(sender, instance, created, **kwargs):
#     if created:
#         subject = "Welcome to Nova VTU!"
#         html_message = render_to_string('emails/welcome_email.html', {'user': instance})
#         message = strip_tags(html_message)  # Plain text fallback

#         send_mail(
#             subject,
#             message,
#             settings.DEFAULT_FROM_EMAIL,
#             [instance.email],
#             html_message=html_message,
#         )

import logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New user created: {instance.username}")
        subject = "Welcome to Nova VTU!"
        html_message = render_to_string('emails/welcome_email.html', {'user': instance})
        message = strip_tags(html_message)

        try:
            send_mail(
                subject,
                message,
                'no-reply@novavtu.com',  # From email address
                [instance.email],
                html_message=html_message,
            )
            logger.info(f"Welcome email sent to {instance.email}")
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
