# wallet/tests.py
import hashlib
import hmac
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from transactions.models import Transaction
from wallet.models import Wallet
from wallet.views import get_paystack_secret_key

User = get_user_model()


class PaystackWebhookTests(TestCase):
    """Test suite for Paystack webhook processing."""

    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse("paystack_webhook")

        self.user = User.objects.create_user(
            username="paystackuser",
            email="paystackuser@example.com",
            password="securepassword123",
            first_name="Paystack",
            last_name="User",
        )
        self.wallet, _ = Wallet.objects.get_or_create(
            user=self.user, defaults={"balance": Decimal("0.00")}
        )
        self.wallet.balance = Decimal("0.00")
        self.wallet.save()

    def _generate_signature(self, payload_bytes: bytes) -> str:
        """Helper to generate HMAC SHA512 signature for a webhook payload."""
        secret = get_paystack_secret_key().encode("utf-8")
        return hmac.new(secret, payload_bytes, hashlib.sha512).hexdigest()

    def test_valid_charge_success_credits_wallet(self):
        """Valid charge.success webhook credits user's wallet with exact amount."""
        payload_data = {
            "event": "charge.success",
            "data": {
                "reference": "ref_valid_1001",
                "amount": 500000,  # ₦5,000 in kobo
                "customer": {
                    "email": "paystackuser@example.com",
                },
            },
        }
        payload_bytes = json.dumps(payload_data).encode("utf-8")
        sig = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )

        self.assertEqual(response.status_code, 200)

        # Verify wallet credited
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("5000.00"))

        # Verify transaction record
        tx = Transaction.objects.get(reference="ref_valid_1001")
        self.assertEqual(tx.wallet, self.wallet)
        self.assertEqual(tx.transaction_type, "funding")
        self.assertEqual(tx.amount, Decimal("5000.00"))
        self.assertEqual(tx.description, "Paystack Webhook Deposit")
        self.assertEqual(tx.status, "completed")

    def test_replaying_webhook_idempotency(self):
        """Replaying exact same webhook payload/reference returns HTTP 200 without double-crediting."""
        payload_data = {
            "event": "charge.success",
            "data": {
                "reference": "ref_idempotent_2002",
                "amount": 250000,  # ₦2,500 in kobo
                "customer": {
                    "email": "paystackuser@example.com",
                },
            },
        }
        payload_bytes = json.dumps(payload_data).encode("utf-8")
        sig = self._generate_signature(payload_bytes)

        # First request
        first_resp = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )
        self.assertEqual(first_resp.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("2500.00"))

        # Replay request
        replay_resp = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )
        self.assertEqual(replay_resp.status_code, 200)

        # Balance must remain unchanged (no double crediting)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("2500.00"))

        # Exactly 1 transaction created
        self.assertEqual(
            Transaction.objects.filter(reference="ref_idempotent_2002").count(),
            1,
        )

    def test_missing_signature_returns_400(self):
        """Missing x-paystack-signature header returns HTTP 400."""
        payload_data = {
            "event": "charge.success",
            "data": {
                "reference": "ref_missing_sig",
                "amount": 100000,
                "customer": {
                    "email": "paystackuser@example.com",
                },
            },
        }
        payload_bytes = json.dumps(payload_data).encode("utf-8")

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertFalse(Transaction.objects.filter(reference="ref_missing_sig").exists())

    def test_forged_signature_returns_400(self):
        """Forged or invalid x-paystack-signature header returns HTTP 400."""
        payload_data = {
            "event": "charge.success",
            "data": {
                "reference": "ref_forged_sig",
                "amount": 100000,
                "customer": {
                    "email": "paystackuser@example.com",
                },
            },
        }
        payload_bytes = json.dumps(payload_data).encode("utf-8")

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE="invalid_forged_signature_hex",
        )

        self.assertEqual(response.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertFalse(Transaction.objects.filter(reference="ref_forged_sig").exists())

    def test_nonexistent_customer_email_returns_404(self):
        """Webhook for a non-existent customer email returns HTTP 404 gracefully."""
        payload_data = {
            "event": "charge.success",
            "data": {
                "reference": "ref_nonexistent_user",
                "amount": 100000,
                "customer": {
                    "email": "ghostuser@example.com",
                },
            },
        }
        payload_bytes = json.dumps(payload_data).encode("utf-8")
        sig = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Transaction.objects.filter(reference="ref_nonexistent_user").exists())

    def test_nonexistent_wallet_returns_404(self):
        """Webhook when user exists but has no wallet returns HTTP 404 gracefully."""
        # Delete user's wallet
        Wallet.objects.filter(user=self.user).delete()

        payload_data = {
            "event": "charge.success",
            "data": {
                "reference": "ref_no_wallet",
                "amount": 100000,
                "customer": {
                    "email": "paystackuser@example.com",
                },
            },
        }
        payload_bytes = json.dumps(payload_data).encode("utf-8")
        sig = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )

        self.assertEqual(response.status_code, 404)

    def test_other_event_type_acknowledged_with_200(self):
        """Non charge.success events are acknowledged with HTTP 200 without crediting."""
        payload_data = {
            "event": "charge.failed",
            "data": {
                "reference": "ref_failed_charge",
                "amount": 100000,
                "customer": {
                    "email": "paystackuser@example.com",
                },
            },
        }
        payload_bytes = json.dumps(payload_data).encode("utf-8")
        sig = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertFalse(Transaction.objects.filter(reference="ref_failed_charge").exists())

    def test_malformed_json_returns_400(self):
        """Malformed JSON payload returns HTTP 400."""
        payload_bytes = b"not a valid json payload"
        sig = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_data_fields_returns_400(self):
        """Missing required fields in charge.success payload returns HTTP 400."""
        payload_data = {
            "event": "charge.success",
            "data": {
                "reference": "ref_missing_data",
                # missing customer and amount
            },
        }
        payload_bytes = json.dumps(payload_data).encode("utf-8")
        sig = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_deposit_amount_returns_400(self):
        """Zero or negative amount returns HTTP 400."""
        payload_data = {
            "event": "charge.success",
            "data": {
                "reference": "ref_zero_amount",
                "amount": 0,
                "customer": {
                    "email": "paystackuser@example.com",
                },
            },
        }
        payload_bytes = json.dumps(payload_data).encode("utf-8")
        sig = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )

        self.assertEqual(response.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))


class WalletViewTests(TestCase):
    """Test wallet pages and standard views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="viewuser",
            email="viewuser@example.com",
            password="viewpassword123",
        )
        self.wallet, _ = Wallet.objects.get_or_create(
            user=self.user, defaults={"balance": Decimal("1000.00")}
        )
        self.wallet.balance = Decimal("1000.00")
        self.wallet.save()
        self.client.login(username="viewuser", password="viewpassword123")

    def test_wallet_info_page_authenticated(self):
        """Wallet info page displays balance and recent transactions."""
        response = self.client.get(reverse("wallet_info"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1,000")

    def test_fund_wallet_page_get(self):
        """Fund wallet page displays paystack public key."""
        response = self.client.get(reverse("fund_wallet"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "viewuser@example.com")

    def test_fund_wallet_post_returns_bad_request(self):
        """POST to fund_wallet returns 400 instructing JS usage."""
        response = self.client.post(reverse("fund_wallet"))
        self.assertEqual(response.status_code, 400)
