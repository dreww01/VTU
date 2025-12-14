# wallet/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Wallet
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Automatically create a wallet when a new user is created.
    """
    if created:
        Wallet.objects.create(
            user=instance,
            balance=Decimal('0.00')
        )
        logger.info(f" Wallet automatically created for user: {instance.username}")