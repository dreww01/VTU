# wallet/models.py
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

logger = logging.getLogger(__name__)

MAX_TRANSACTION = Decimal("100000")  # ₦100,000
MAX_BALANCE = Decimal("1000000")  # ₦1,000,000


class Wallet(models.Model):
    """User's wallet for storing funds and making VTU purchases."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="The user who owns this wallet",
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Current wallet balance in Naira",
    )
    currency = models.CharField(
        max_length=3, default="NGN", help_text="Currency code (NGN for Naira)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user.username}'s Wallet - ₦{self.balance}"

    def clean(self):
        """Validate wallet data before saving."""
        if self.balance is None:
            raise ValidationError("Balance cannot be None")

        try:
            self.balance = Decimal(str(self.balance))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(f"Invalid balance value: {self.balance}")

        if self.balance < 0:
            raise ValidationError("Balance cannot be negative")

        if self.balance > MAX_BALANCE:
            raise ValidationError(f"Balance cannot exceed ₦{MAX_BALANCE}")

        self.balance = self.balance.quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        """Override save to always validate before saving."""
        self.clean()
        super().save(*args, **kwargs)

    def deposit(self, amount, description="Paystack Deposit", reference=None):
        """
        Add money to wallet (used for Paystack deposits).
        Returns the created Transaction object.
        """
        from transactions.models import Transaction  # ✅ Import here to avoid circular import

        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            logger.error(f"Invalid deposit amount for {self.user.username}: {amount}")
            raise ValueError(f"Invalid amount: {amount}")

        if amount <= 0:
            raise ValueError("Amount must be positive")

        amount = amount.quantize(Decimal("0.01"))

        if amount > MAX_TRANSACTION:
            raise ValueError(f"Transaction cannot exceed ₦{MAX_TRANSACTION}")

        new_balance = self.balance + amount
        if new_balance > MAX_BALANCE:
            raise ValueError(f"Would exceed maximum balance of ₦{MAX_BALANCE}")

        self.balance = new_balance
        self.save()

        transaction = Transaction.objects.create(
            wallet=self,
            transaction_type="funding",
            amount=amount,
            description=description,
            reference=reference,
            status="completed",
        )

        logger.info(f"Deposited ₦{amount} to {self.user.username}. New balance: ₦{self.balance}")
        return transaction

    def purchase(self, amount, description):
        """
        Remove money for VTU purchases (airtime, data, electricity, etc).
        Returns the created Transaction object.
        """
        from transactions.models import Transaction  # ✅ Import here to avoid circular import

        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            logger.error(f"Invalid purchase amount for {self.user.username}: {amount}")
            raise ValueError(f"Invalid amount: {amount}")

        if amount <= 0:
            raise ValueError("Amount must be positive")

        amount = amount.quantize(Decimal("0.01"))

        if amount > MAX_TRANSACTION:
            raise ValueError(f"Transaction cannot exceed ₦{MAX_TRANSACTION}")

        if self.balance < amount:
            logger.warning(
                f"Insufficient funds for {self.user.username}. Balance: ₦{self.balance}, Attempted: ₦{amount}"
            )
            raise ValueError(f"Insufficient funds. Balance: ₦{self.balance}")

        self.balance -= amount
        self.save()

        transaction = Transaction.objects.create(
            wallet=self,
            transaction_type="purchase",
            amount=amount,
            description=description,
            status="completed",
        )

        logger.info(f"Purchase ₦{amount} from {self.user.username}. New balance: ₦{self.balance}")
        return transaction
