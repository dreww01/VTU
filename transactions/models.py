# transactions/models.py
from django.db import models
from django.contrib.auth.models import User
from wallet.models import Wallet 
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)

MAX_TRANSACTION = Decimal('100000')  # ₦100,000
MAX_BALANCE = Decimal('1000000')     # ₦1,000,000

class Transaction(models.Model):
    
    TRANSACTION_TYPES = (
        ('funding', 'Funding'),
        ('purchase', 'Purchase'),
    )

    STATUS_CHOICES = (
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    wallet = models.ForeignKey(
        'wallet.Wallet', 
        on_delete=models.CASCADE,
        help_text="The wallet this transaction belongs to"
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        help_text="Type of transaction (funding or purchase)"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Transaction amount in Naira"
    )
    description = models.CharField(
        max_length=255,
        help_text="Description (e.g., 'Paystack Deposit', 'MTN Airtime')"
    )
    reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="Unique reference number (used for Paystack deposits)"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='completed',
        help_text="Status: completed or failed"
    )

    token = models.CharField(max_length=100, blank=True, null=True)


    # requeries failed transactions with the provider and cancels x lifetime pending automatically
    requery_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this transaction has been rechecked with the provider."
    )
    last_requery_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time we called the provider to recheck this transaction."
    )
    provider_status = models.CharField(
        max_length=50,
        blank=True,
        help_text="Latest known status from provider (e.g. delivered, pending, failed)."
    )
    provider_response = models.JSONField(
        null=True,
        blank=True,
        help_text="Last raw provider response for support/debugging."
    )
    requires_manual_review = models.BooleanField(
        default=False,
        help_text="Flag for customer support to manually review this transaction."
    )

    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['wallet', '-timestamp']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_type']),
        ]

    def __str__(self):
        return f"{self.transaction_type.upper()} ₦{self.amount} - {self.wallet.user.username}"

    # ❌ REMOVE deposit() and purchase() methods from here
    # They belong in the Wallet model, not Transaction model

    def clean(self):
        """Validate transaction data before saving."""
        if self.amount is None:
            raise ValidationError("Amount cannot be None")
        
        try:
            self.amount = Decimal(str(self.amount))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(f"Invalid amount value: {self.amount}")
        
        if self.amount <= 0:
            raise ValidationError("Amount must be greater than zero")
        
        if self.amount > MAX_TRANSACTION:
            raise ValidationError(f"Amount cannot exceed ₦{MAX_TRANSACTION}")
        
        self.amount = self.amount.quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        """Override save to always validate before saving."""
        self.clean()
        super().save(*args, **kwargs)
        logger.info(f"Transaction saved: {self.transaction_type} {self.amount} NGN for {self.wallet.user.username}")



class AppSettings(models.Model):
    """
    Global app settings - only one row should exist.
    Admins can toggle features on/off.
    """
    fraud_checks_enabled = models.BooleanField(
        default=True,
        help_text="Enable/disable fraud detection checks (transaction limits, hourly limits, etc.)"
    )
    
    maintenance_mode = models.BooleanField(
        default=False,
        help_text="Put the app in maintenance mode (blocks all transactions)"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "App Settings"
        verbose_name_plural = "App Settings"
    
    def __str__(self):
        return "App Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create the settings instance"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
    
    def save(self, *args, **kwargs):
        """Ensure only one settings instance exists"""
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of settings"""
        pass