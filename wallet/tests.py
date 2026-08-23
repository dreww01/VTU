import hashlib
import hmac
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from transactions.models import Transaction
from wallet.models import MAX_BALANCE, MAX_TRANSACTION, Wallet

User = get_user_model()
TEST_SECRET_KEY = "sk_test_mock_secret_key_12345"


@override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
class PaystackWebhookTests(TestCase):
    """Test suite for Paystack webhook processing."""

    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse("paystack_webhook")
        self.secret_key = TEST_SECRET_KEY

        self.user = User.objects.create_user(
            username="webhookuser",
            email="webhookuser@example.com",
            password="testpassword123",
            first_name="Webhook",
            last_name="User",
        )
        self.wallet, _ = Wallet.objects.get_or_create(user=self.user)
        self.wallet.balance = Decimal("0.00")
        self.wallet.save()

    def _generate_signature(self, payload_bytes: bytes, key: str | None = None) -> str:
        secret = (key or self.secret_key).encode("utf-8")
        return hmac.new(secret, payload_bytes, hashlib.sha512).hexdigest()

    def _make_charge_success_payload(
        self,
        reference: str = "T1234567890",
        amount_kobo: int = 500000,
        email: str = "webhookuser@example.com",
    ) -> dict:
        return {
            "event": "charge.success",
            "data": {
                "id": 1001,
                "domain": "test",
                "status": "success",
                "reference": reference,
                "amount": amount_kobo,
                "currency": "NGN",
                "channel": "card",
                "customer": {
                    "id": 2001,
                    "first_name": "Webhook",
                    "last_name": "User",
                    "email": email,
                },
            },
        }

    def test_valid_charge_success_credits_wallet(self):
        """1. Valid charge.success webhook credits the user's wallet with the exact amount."""
        payload_dict = self._make_charge_success_payload(
            reference="TEST_REF_001", amount_kobo=250000, email=self.user.email
        )
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )

        self.assertEqual(response.status_code, 200)

        # Verify wallet balance: 250,000 kobo = 2,500.00 NGN
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("2500.00"))

        # Verify transaction record
        tx = Transaction.objects.get(reference="TEST_REF_001")
        self.assertEqual(tx.wallet, self.wallet)
        self.assertEqual(tx.amount, Decimal("2500.00"))
        self.assertEqual(tx.transaction_type, "funding")
        self.assertEqual(tx.description, "Paystack Webhook Deposit")
        self.assertEqual(tx.status, "completed")

    def test_charge_success_case_insensitive_email_credits_wallet(self):
        """Case-insensitive email match in webhook payload credits the user's wallet."""
        # Payload has mixed-case email while user.email is lowercase
        payload_dict = self._make_charge_success_payload(
            reference="CASE_TEST_REF_001",
            amount_kobo=300000,
            email="WebHookUser@EXAMPLE.Com",
        )
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )

        self.assertEqual(response.status_code, 200)

        # Verify wallet balance: 300,000 kobo = 3,000.00 NGN
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("3000.00"))

        # Verify transaction record
        tx = Transaction.objects.get(reference="CASE_TEST_REF_001")
        self.assertEqual(tx.wallet, self.wallet)
        self.assertEqual(tx.amount, Decimal("3000.00"))

    def test_replay_webhook_idempotency(self):
        """2. Replaying the exact same webhook payload/reference returns HTTP 200 without double-crediting."""
        payload_dict = self._make_charge_success_payload(
            reference="IDEMPOTENT_REF_001", amount_kobo=500000, email=self.user.email
        )
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        # First webhook call
        response1 = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )
        self.assertEqual(response1.status_code, 200)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("5000.00"))
        self.assertEqual(Transaction.objects.filter(reference="IDEMPOTENT_REF_001").count(), 1)

        # Replay the exact same webhook
        response2 = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )
        self.assertEqual(response2.status_code, 200)

        # Balance must NOT be credited twice
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("5000.00"))
        self.assertEqual(Transaction.objects.filter(reference="IDEMPOTENT_REF_001").count(), 1)

    def test_missing_signature_header_returns_400(self):
        """3a. Missing x-paystack-signature header returns HTTP 400."""
        payload_dict = self._make_charge_success_payload(reference="NO_SIG_REF")
        payload_bytes = json.dumps(payload_dict).encode("utf-8")

        # Request with no signature header
        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertFalse(Transaction.objects.filter(reference="NO_SIG_REF").exists())

    def test_empty_signature_header_returns_400(self):
        """3b. Empty x-paystack-signature header returns HTTP 400."""
        payload_dict = self._make_charge_success_payload(reference="EMPTY_SIG_REF")
        payload_bytes = json.dumps(payload_dict).encode("utf-8")

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": ""},
        )
        self.assertEqual(response.status_code, 400)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    def test_forged_signature_returns_400(self):
        """3c. Forged x-paystack-signature header returns HTTP 400."""
        payload_dict = self._make_charge_success_payload(reference="FORGED_REF")
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        bad_signature = self._generate_signature(payload_bytes, key="wrong_secret_key")

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": bad_signature},
        )
        self.assertEqual(response.status_code, 400)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertFalse(Transaction.objects.filter(reference="FORGED_REF").exists())

    def test_nonexistent_customer_email_returns_404(self):
        """4. Webhook for a non-existent customer email returns HTTP 404 gracefully."""
        payload_dict = self._make_charge_success_payload(
            reference="UNKNOWN_CUST_REF",
            amount_kobo=300000,
            email="nonexistent.customer@example.com",
        )
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )
        self.assertEqual(response.status_code, 404)

        # No transaction created
        self.assertFalse(Transaction.objects.filter(reference="UNKNOWN_CUST_REF").exists())

    def test_unhandled_event_returns_200(self):
        """Unhandled events (like transfer.success) return 200 without altering wallet."""
        payload_dict = {
            "event": "transfer.success",
            "data": {
                "amount": 100000,
                "reference": "TRANSFER_REF_001",
                "customer": {"email": self.user.email},
            },
        }
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )
        self.assertEqual(response.status_code, 200)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertFalse(Transaction.objects.filter(reference="TRANSFER_REF_001").exists())

    def test_invalid_json_payload_returns_400(self):
        """Malformed JSON payload returns HTTP 400."""
        payload_bytes = b"invalid-json-content{}"
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_required_fields_in_payload_returns_400(self):
        """Payload missing email or reference returns HTTP 400."""
        payload_dict = {
            "event": "charge.success",
            "data": {
                "amount": 50000,
                # missing reference and customer
            },
        }
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_amount_returns_400(self):
        """Payload with non-numeric amount returns HTTP 400."""
        payload_dict = self._make_charge_success_payload(reference="INVALID_AMT_REF")
        payload_dict["data"]["amount"] = "invalid_amount_abc"
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )
        self.assertEqual(response.status_code, 400)

    def test_exceeding_max_transaction_returns_400(self):
        """Payload exceeding max transaction limit returns HTTP 400."""
        # MAX_TRANSACTION is 100,000 NGN = 10,000,000 kobo
        payload_dict = self._make_charge_success_payload(
            reference="EXCEED_LIMIT_REF",
            amount_kobo=20000000,  # 200,000 NGN
            email=self.user.email,
        )
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )
        self.assertEqual(response.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    def test_get_method_not_allowed(self):
        """GET request to webhook endpoint returns 405 Method Not Allowed."""
        response = self.client.get(self.webhook_url)
        self.assertEqual(response.status_code, 405)


class WalletModelTests(TestCase):
    """Test suite for Wallet model operations."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="modeluser",
            email="modeluser@example.com",
            password="testpassword123",
        )
        self.wallet, _ = Wallet.objects.get_or_create(user=self.user)

    def test_wallet_deposit_success(self):
        """Deposit updates balance and creates transaction."""
        tx = self.wallet.deposit(
            amount=Decimal("5000.00"),
            description="Test Deposit",
            reference="DEP_001",
        )
        self.assertEqual(self.wallet.balance, Decimal("5000.00"))
        self.assertEqual(tx.amount, Decimal("5000.00"))
        self.assertEqual(tx.reference, "DEP_001")
        self.assertEqual(tx.transaction_type, "funding")

    def test_wallet_deposit_invalid_amounts(self):
        """Deposit fails for non-positive amounts or exceeding limits."""
        with self.assertRaises(ValueError):
            self.wallet.deposit(Decimal("0.00"))

        with self.assertRaises(ValueError):
            self.wallet.deposit(Decimal("-50.00"))

        with self.assertRaises(ValueError):
            self.wallet.deposit(MAX_TRANSACTION + Decimal("1.00"))

    def test_wallet_purchase_success(self):
        """Purchase deducts balance and creates transaction."""
        self.wallet.deposit(Decimal("5000.00"))
        tx = self.wallet.purchase(Decimal("2000.00"), description="MTN Data")
        self.assertEqual(self.wallet.balance, Decimal("3000.00"))
        self.assertEqual(tx.amount, Decimal("2000.00"))
        self.assertEqual(tx.transaction_type, "purchase")

    def test_wallet_purchase_insufficient_funds(self):
        """Purchase fails if balance is insufficient."""
        self.wallet.deposit(Decimal("500.00"))
        with self.assertRaises(ValueError):
            self.wallet.purchase(Decimal("1000.00"), description="MTN Data")


class WalletViewsTests(TestCase):
    """Test suite for Wallet info and fund pages."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="viewuser",
            email="viewuser@example.com",
            password="testpassword123",
        )
        self.wallet, _ = Wallet.objects.get_or_create(user=self.user)

    def test_wallet_info_authenticated(self):
        """Authenticated user can view wallet info."""
        self.client.login(username="viewuser", password="testpassword123")
        response = self.client.get(reverse("wallet_info"))
        self.assertEqual(response.status_code, 200)

    def test_wallet_info_unauthenticated(self):
        """Unauthenticated user redirected to login."""
        response = self.client.get(reverse("wallet_info"))
        self.assertEqual(response.status_code, 302)

    def test_fund_wallet_authenticated(self):
        """Authenticated user can view fund wallet page."""
        self.client.login(username="viewuser", password="testpassword123")
        response = self.client.get(reverse("fund_wallet"))
        self.assertEqual(response.status_code, 200)

    def test_fund_wallet_post_rejected(self):
        """POST to fund_wallet returns 400."""
        self.client.login(username="viewuser", password="testpassword123")
        response = self.client.post(reverse("fund_wallet"))
        self.assertEqual(response.status_code, 400)
