<div align="center">

# 🚀 Nova VTU

### Enterprise-Grade Virtual Top-Up & Utility Payment Platform for Nigeria

*Instant airtime, data bundles, and electricity utility payments backed by robust financial integrity and fraud protection.*

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production--Ready-brightgreen?style=for-the-badge)]()

[Features](#-features) • [Tech Stack](#-tech-stack) • [Quick Start](#-quick-start) • [Architecture](#-project-structure) • [API & Routing](#-application-routing--api-reference) • [VTU Provider](#-vtu-service-provider-integration-vtpass) • [Security & Fraud](#-security-fraud-prevention--rate-limiting) • [Deployment](#-deployment-guides)

</div>

---

## 📋 Table of Contents

- [🌟 Overview](#-overview)
- [✨ Features](#-features)
  - [End-User Capabilities](#end-user-capabilities)
  - [Administrative & Operational Capabilities](#administrative--operational-capabilities)
- [🛠️ Tech Stack & Key Dependencies](#-tech-stack--key-dependencies)
- [📁 Project Structure](#-project-structure)
- [🔐 Complete Environment Variables Reference](#-complete-environment-variables-reference)
- [🚀 Quick Start & Local Development](#-quick-start--local-development)
  - [Prerequisites](#prerequisites)
  - [Step-by-Step Installation](#step-by-step-installation)
- [🌐 Application Routing & API Reference](#-application-routing--api-reference)
  - [Accounts & Authentication](#accounts--authentication)
  - [Wallet Management](#wallet-management)
  - [VTU & Utility Transactions](#vtu--utility-transactions)
  - [System Endpoints](#system-endpoints)
- [🔌 Payment Gateway Integration (Paystack)](#-payment-gateway-integration-paystack)
  - [Wallet Funding Lifecycle](#wallet-funding-lifecycle)
  - [Webhook Signature Verification](#webhook-signature-verification)
- [⚡ VTU Service Provider Integration (VTPass)](#-vtu-service-provider-integration-vtpass)
  - [Supported Services & Disco Providers](#supported-services--disco-providers)
  - [Airtime & Data Variations](#airtime--data-variations)
  - [Electricity Meter Verification & Token Delivery](#electricity-meter-verification--token-delivery)
- [💳 Financial Integrity & Wallet Mechanics](#-financial-integrity--wallet-mechanics)
  - [Atomic Operations & Concurrency Locking](#atomic-operations--concurrency-locking)
  - [Financial Boundary Invariants](#financial-boundary-invariants)
- [🛡️ Security, Fraud Prevention & Rate Limiting](#-security-fraud-prevention--rate-limiting)
  - [Tiered Transaction Limits](#tiered-transaction-limits)
  - [Granular Rate Limiting](#granular-rate-limiting)
  - [Security Headers & Cookie Policies](#security-headers--cookie-policies)
  - [Exception Hierarchy](#exception-hierarchy)
- [⚙️ Management Commands & CLI Utilities](#-management-commands--cli-utilities)
  - [Pending Transaction Re-checker (`recheck_pending_vtu`)](#pending-transaction-re-checker-recheck_pending_vtu)
- [💾 Database Backup & Disaster Recovery](#-database-backup--disaster-recovery)
  - [Automated Compressed Backups (`backup.sh`)](#automated-compressed-backups-backupsh)
  - [Safe Database Restores (`restore.sh`)](#safe-database-restores-restoresh)
- [🐳 Docker & Container Orchestration](#-docker--container-orchestration)
  - [Service Architecture](#service-architecture)
  - [Docker Compose Workflows](#docker-compose-workflows)
- [🚢 Deployment Guides](#-deployment-guides)
  - [1. Google Cloud Run + Neon PostgreSQL (Recommended)](#1-google-cloud-run--neon-postgresql-recommended)
  - [2. Multi-Container Docker Stack](#2-multi-container-docker-stack)
  - [3. Traditional VPS (Nginx + Gunicorn + Systemd)](#3-traditional-vps-nginx--gunicorn--systemd)
- [🧪 Testing & Quality Assurance](#-testing--quality-assurance)
- [DSH Temporal Smoke Test](#dsh-temporal-smoke-test)
- [🔧 Troubleshooting & FAQ](#-troubleshooting--faq)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)
- [🗺️ Roadmap](#-roadmap)

---

## 🌟 Overview

**Nova VTU** is a production-grade Django 6.0+ platform engineered specifically for virtual top-ups and utility bill settlements across Nigeria. Built on top of Python 3.13, it connects end consumers directly to telecom operators (MTN, Airtel, GLO, 9mobile) and regional electricity distribution companies (Discos) via the VTPass API, backed by seamless wallet funding through Paystack.

### Core Architectural Values

- 🔒 **Defensive Financial Engineering:** Strict database row-level locking (`select_for_update`) and atomic transactions eliminate race conditions and double-spending across wallet operations.
- ⚡ **Asynchronous Resiliency:** Intelligent query and requery workflows automatically reconcile delayed provider responses without stranding user funds.
- 🛡️ **Tiered Risk & Fraud Engine:** Real-time single, hourly, and daily transaction rate and volume throttling tailored by KYC verification tiers.
- 📧 **Automated Multichannel Communications:** Instant purchase notifications, prepaid electricity token delivery, and wallet receipts via Resend SMTP.
- 🎨 **Modern User & Admin Interfaces:** Responsive mobile-first UI powered by Tailwind CSS, coupled with an operational command center built on Django Unfold.

---

## ✨ Features

### End-User Capabilities

| Capability | Technical Detail |
|---|---|
| 🔐 **Account Lifecycle** | Secure user registration, authentication, profile management with avatar uploads, and email-based password reset. |
| 💳 **Instant Wallet Funding** | Direct wallet top-up via Paystack checkout with cryptographic webhook signature validation. |
| 📱 **Airtime Purchase** | Instant top-up across MTN, Airtel, GLO, and 9mobile with phone number validation. |
| 📊 **Data Bundles** | Flexible data bundle procurement from daily micro-bundles to monthly bulk subscriptions. |
| ⚡ **Electricity Bill Payment** | Prepaid meter validation via VTPass Merchant Verify before payment, with instant token generation on receipt. |
| 📜 **Auditable Transaction History** | Searchable, filterable transaction histories with dedicated receipt views for airtime, data, and electricity. |
| 📧 **Transaction Receipts** | Real-time HTML email delivery for top-up confirmations and electricity tokens. |

### Administrative & Operational Capabilities

- 📊 **Django Unfold Command Center:** Clean dashboard monitoring users, wallets, transaction statuses, and provider logs.
- 🔍 **Automated Transaction Re-checker:** Custom Django management command (`recheck_pending_vtu`) to poll provider APIs and resolve pending states.
- ⚙️ **Runtime App Settings:** Database-driven toggles for platform maintenance mode and automated fraud controls.
- 📈 **Auditing & Telemetry:** Verbose structured logging across `accounts`, `wallet`, and `transactions` domains.

---

## 🛠️ Tech Stack & Key Dependencies

### Backend & Core Systems
- **Language:** Python 3.13+
- **Framework:** Django 6.0+
- **Database Engine:** PostgreSQL 16+ (Production) / SQLite3 (Development & In-Memory Test Suite)
- **Database Adapter:** `dj-database-url`, `psycopg[binary]>=3.3.2` (Psycopg 3)
- **HTTP Client:** `httpx 0.28+` for resilient external API integration
- **WSGI / ASGI Servers:** `gunicorn 23.0+`

### Frontend & Templating
- **Styling:** Tailwind CSS (responsive mobile-first design)
- **Icons:** Heroicons & Font Awesome
- **Admin Theme:** `django-unfold 0.73+`
- **Static Assets:** `whitenoise 6.8+` with compressed manifest storage

### Integrations & Services
- **Payment Processing:** Paystack API
- **Telecom & Utilities Provider:** VTPass API (Airtime, Data, Electricity)
- **Transactional Email:** Resend SMTP
- **Cloud Storage:** Google Cloud Storage (`django-storages[google]`)
- **Rate Limiting:** `django-ratelimit 4.1+` with custom middleware

---

## 📁 Project Structure

```
VTU/
├── accounts/                      # Authentication & user profile domain
│   ├── migrations/                # Database migrations for accounts
│   ├── admin.py                   # Custom Unfold admin registration
│   ├── apps.py                    # App configuration & signal registration
│   ├── forms.py                   # Registration, login, profile, and password reset forms
│   ├── models.py                  # UserProfile model & KYC tier tracking
│   ├── signals.py                 # Automatic UserProfile creation on User post_save
│   ├── tests.py                   # Comprehensive unit & integration tests
│   ├── urls.py                    # Account routing (/login, /register, /account/profile, etc.)
│   ├── validators.py              # Phone number & custom input validators
│   └── views.py                   # Auth controllers & dashboard renderers
│
├── wallet/                        # Financial ledger & wallet balance management
│   ├── migrations/                # Wallet schema migrations
│   ├── admin.py                   # Wallet & funding transaction admin views
│   ├── apps.py                    # Wallet app configuration
│   ├── models.py                  # Wallet model (atomic deposit & purchase logic)
│   ├── urls.py                    # Wallet routes (/wallet/info, /wallet/fund, etc.)
│   └── views.py                   # Paystack initialization, verification, & webhook handlers
│
├── transactions/                  # VTU services, telecom & utility providers
│   ├── management/
│   │   └── commands/
│   │       └── recheck_pending_vtu.py  # Periodic pending transaction reconciler
│   ├── migrations/                # Schema migrations for transactions & app settings
│   ├── providers/                 # Third-party provider client adapters
│   │   ├── exceptions.py          # Provider-level error definitions
│   │   └── vtpass.py              # VTPass API client (Airtime, Data, Electricity, Verify)
│   ├── services/                  # Encapsulated business logic services
│   │   ├── airtime.py             # Airtime top-up execution service
│   │   ├── data.py                # Data bundle purchase service & plan catalog
│   │   ├── electricity.py         # Electricity bill payment service & DISCO mappings
│   │   ├── fraud_check.py         # Multi-tiered fraud & rate limit evaluator
│   │   ├── verification.py        # Meter validation & transaction status requery engine
│   │   └── vtu_service.py         # Service routing facade
│   ├── admin.py                   # Transaction & AppSettings administration
│   ├── models.py                  # Transaction and AppSettings models
│   ├── urls.py                    # Service routes (/airtime, /data, /electricity, receipts)
│   └── views.py                   # Service purchase views & receipt generators
│
├── config/                        # Django application configuration & orchestration
│   ├── asgi.py                    # ASGI application entrypoint
│   ├── middleware.py              # Custom RateLimitMiddleware & security hooks
│   ├── settings.py                # Environment-aware Django settings
│   ├── urls.py                    # Root URL router & healthcheck endpoint
│   └── wsgi.py                    # WSGI application entrypoint for Gunicorn
│
├── docs/                          # In-depth architectural & deployment guides
│   ├── DEPLOY.md                  # Quick Cloud Run + Neon PostgreSQL deployment
│   └── GCP_DEPLOYMENT_GUIDE.md    # Comprehensive GCP deployment guide with CI/CD
│
├── nginx/                         # Reverse proxy configuration
│   ├── conf.d/
│   │   └── nova-vtu.conf          # Nginx virtual host with SSL & rate limit proxies
│   └── nginx.conf                 # Master Nginx configuration
│
├── scripts/                       # Operational & disaster recovery utilities
│   └── backup/
│       ├── backup.sh              # PostgreSQL backup script with gzip & S3 upload
│       └── restore.sh             # Safe database restoration script
│
├── templates/                     # Django HTML templates
│   ├── accounts/                  # Login, register, profile, password reset, dashboard
│   ├── emails/                    # HTML email receipts & onboarding templates
│   ├── errors/                    # Custom error pages (400, 403, 404, 429, 500)
│   ├── includes/                  # Reusable form errors & alert banners
│   ├── transactions/              # Airtime, data, electricity purchase & receipt templates
│   ├── wallet/                    # Wallet info, funding, and payment confirmation
│   └── layout.html                # Base layout with navigation & responsive drawer
│
├── media/                         # User-uploaded files (avatars)
├── staticfiles/                   # Collected static assets for Whitenoise
├── docker-compose.yml             # Local & production multi-container orchestration
├── Dockerfile                     # Multi-stage production container image
├── pyproject.toml                 # Project metadata and locked dependency manifests
└── README.md                      # Platform documentation
```

---

## 🔐 Complete Environment Variables Reference

Configure these variables in your `.env` file (or Google Cloud Secret Manager / Docker secrets in production):

| Variable | Type | Default / Example | Required | Subsystem / Purpose |
|---|---|---|---|---|
| `SECRET_KEY` | String | `django-insecure-...` | **Yes** | Django cryptographic signing key. Must be unique and unpredictable in production. |
| `DEBUG` | Boolean | `True` | No | Enables debug mode. **Must be set to `False` in production.** |
| `ALLOWED_HOSTS` | Comma-separated | `127.0.0.1,localhost,.run.app` | No | Whitelist of host/domain names that this Django site can serve. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated | `https://*.run.app` | No | Trusted origins for unsafe HTTP requests (e.g. POST) under HTTPS. |
| `DATABASE_URL` | URI String | `sqlite:///db.sqlite3` | No | Database connection URL. Supports PostgreSQL (`postgresql://user:pass@host:5432/db?sslmode=require`). |
| `PAYSTACK_SECRET_KEY` | String | `sk_test_...` / `sk_live_...` | **Yes** | Paystack secret key used for backend API authorization and webhook verification. |
| `PAYSTACK_PUBLIC_KEY` | String | `pk_test_...` / `pk_live_...` | **Yes** | Paystack public key used in client-side transaction initialization. |
| `VTPASS_BASE_URL` | URL | `https://sandbox.vtpass.com/api` | No | VTPass API base endpoint. Switch to `https://vtpass.com/api` in production. |
| `VTPASS_API_KEY` | String | `your_api_key` | **Yes** | VTPass user account API key. |
| `VTPASS_SECRET_KEY` | String | `SK_your_secret_key` | **Yes** | VTPass secret key used for authenticating VTU purchase requests. |
| `VTPASS_PUBLIC_KEY` | String | `PK_your_public_key` | **Yes** | VTPass public key for service queries. |
| `RESEND_API_KEY` | String | `re_...` | No | Resend API key for sending transactional emails over SMTP. |
| `DEFAULT_FROM_EMAIL` | String | `Nova VTU <delivered@resend.dev>` | No | Default sender address for receipts and notifications. |
| `GS_BUCKET_NAME` | String | `nova-vtu-media` | No | Optional Google Cloud Storage bucket name for persistent user media files. |
| `POSTGRES_DB` | String | `nova_vtu` | No | Database name for Docker / PostgreSQL scripts. |
| `POSTGRES_USER` | String | `nova_vtu` | No | Database username for Docker / PostgreSQL scripts. |
| `POSTGRES_PASSWORD` | String | `nova_vtu_password` | No | Database password for Docker / PostgreSQL scripts. |
| `S3_BUCKET` | String | `my-backup-bucket` | No | Optional AWS S3 bucket for automated database backup archiving. |
| `AWS_ACCESS_KEY_ID` | String | `AKIA...` | No | AWS access key for S3 backup uploads. |
| `AWS_SECRET_ACCESS_KEY` | String | `wJalr...` | No | AWS secret key for S3 backup uploads. |
| `AWS_REGION` | String | `us-east-1` | No | AWS region for S3 backup bucket. |

---

## 🚀 Quick Start & Local Development

### Prerequisites

- **Python:** 3.13 or higher
- **Package Manager:** `uv` (recommended) or `pip`
- **Git**

### Step-by-Step Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/dreww01/VTU.git
   cd VTU
   ```

2. **Set Up a Virtual Environment:**
   ```bash
   # Using uv (fastest)
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Or using standard python venv
   python3.13 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   # Using uv
   uv sync

   # Or using pip
   pip install -e .
   ```

4. **Initialize Environment Variables:**
   ```bash
   cp .env.example .env
   ```
   Generate a secure secret key and set it in `.env`:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

5. **Run Migrations & Initialize Database:**
   ```bash
   python manage.py migrate
   ```

6. **Create an Administrator Account:**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the Development Server:**
   ```bash
   python manage.py runserver 127.0.0.1:8000
   ```

8. **Verify System Endpoints:**
   - **User Portal:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - **Admin Command Center:** [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
   - **Health Check:** [http://127.0.0.1:8000/health/](http://127.0.0.1:8000/health/) (returns `{"status": "healthy"}`)

---

## 🌐 Application Routing & API Reference

### Accounts & Authentication

| HTTP Method | Route URL | View Name | Auth Required | Description |
|---|---|---|---|---|
| `GET` | `/` | `dashboard` | Yes | Main dashboard overview (balance, recent transactions, quick actions). |
| `GET`, `POST` | `/login/` | `login` | No | User authentication endpoint with rate limiting (`5/min`). |
| `GET`, `POST` | `/register/` | `register` | No | New user onboarding with profile initialization (`3/min`). |
| `GET`, `POST` | `/logout/` | `logout` | Yes | Terminates authenticated user session. |
| `GET`, `POST` | `/password_reset/` | `password_reset` | No | Dispatches one-time password reset verification codes (`3/min`). |
| `GET`, `POST` | `/password_reset_confirm/` | `password_reset_confirm` | No | Validates reset token and sets new password. |
| `GET`, `POST` | `/account/profile/` | `profile` | Yes | Displays and updates user profile, names, phone number, and avatar. |
| `GET` | `/services/` | `vtu_services` | Yes | Central navigation hub for all top-up and utility services. |

### Wallet Management

| HTTP Method | Route URL | View Name | Auth Required | Description |
|---|---|---|---|---|
| `GET` | `/wallet/info/` | `wallet_info` | Yes | Returns current wallet balance and recent ledger items. |
| `GET`, `POST` | `/wallet/fund/` | `fund_wallet` | Yes | Initiates a Paystack checkout transaction to deposit funds. |
| `GET` | `/wallet/verify/<reference>/` | `verify_payment` | Yes | Verifies Paystack transaction reference and credits wallet balance. |
| `POST` | `/wallet/webhook/` | `paystack_webhook` | No | Paystack webhook receiver validating `x-paystack-signature` HMAC. |

### VTU & Utility Transactions

| HTTP Method | Route URL | View Name | Auth Required | Description |
|---|---|---|---|---|
| `GET` | `/transactions/history/` | `transaction_history` | Yes | Paginated and filterable transaction log with search options. |
| `GET`, `POST` | `/transactions/airtime/buy/` | `buy_airtime` | Yes | Purchase airtime for MTN, Airtel, GLO, or 9mobile. |
| `GET`, `POST` | `/transactions/data/buy/` | `buy_data` | Yes | Purchase data bundles across Nigerian telecom networks. |
| `GET`, `POST` | `/transactions/electricity/buy/` | `pay_electricity` | Yes | Verify meter and purchase prepaid/postpaid electricity units. |
| `GET` | `/transactions/airtime/receipt/<reference>/` | `airtime_receipt` | Yes | Download or view formatted receipt for airtime purchase. |
| `GET` | `/transactions/data/receipt/<reference>/` | `data_receipt` | Yes | Download or view formatted receipt for data purchase. |
| `GET` | `/transactions/electricity/receipt/<reference>/` | `electricity_receipt` | Yes | View electricity token receipt with meter information. |
| `POST` | `/transactions/webhook/vtpass/` | `vtpass_webhook` | No | VTPass asynchronous transaction status notification endpoint. |

### System Endpoints

| HTTP Method | Route URL | Description |
|---|---|---|
| `GET` | `/health/` | Health check endpoint returning HTTP 200 `{"status": "healthy"}` for load balancers. |
| `GET`, `POST` | `/admin/` | Unfold administration command center. |

---

## 🔌 Payment Gateway Integration (Paystack)

### Wallet Funding Lifecycle

```
[ User ] --( 1. Enter Amount >= ₦100 )--> [ Nova VTU /wallet/fund/ ]
                                                      |
                                         ( 2. Initialize Transaction )
                                                      |
                                                      v
[ Paystack Checkout ] <----------------- [ Paystack API ]
        |
   ( 3. Payment Complete )
        |
        +-----------------------------------+
        |                                   |
( 4. User Redirect )              ( 5. Webhook POST )
        |                                   |
        v                                   v
[ /wallet/verify/<ref> ]        [ /wallet/webhook/ ]
        |                                   |
        +-------------> [ Atomic Deposit ] <-+
                        - Row-level lock (`select_for_update`)
                        - Balance integrity check
                        - Credit Wallet & Mark Completed
```

### Webhook Signature Verification

All incoming Paystack webhook requests are cryptographically validated against your `PAYSTACK_SECRET_KEY` using HMAC SHA512:

```python
# Verification implementation detail in wallet/views.py
paystack_signature = request.headers.get("x-paystack-signature")
computed_hash = hmac.new(
    settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
    request.body,
    hashlib.sha512
).hexdigest()

if not hmac.compare_digest(computed_hash, paystack_signature):
    return HttpResponseForbidden("Invalid signature")
```

---

## ⚡ VTU Service Provider Integration (VTPass)

### Supported Services & Disco Providers

Nova VTU maps internal service identifiers to VTPass product gateways:

### Airtime & Data Variations

#### 1. Airtime Top-Up
- **Networks:** MTN (`mtn`), Airtel (`airtel`), GLO (`glo`), 9mobile (`etisalat`)
- **Validation:** Nigerian phone format validation (`080...`, `070...`, `090...`, `081...`, `+234...`)
- **Minimum Purchase:** ₦50.00

#### 2. Data Bundles
- **Networks:** MTN Data (`mtn-data`), Airtel Data (`airtel-data`), GLO Data (`glo-data`), 9mobile Data (`etisalat-data`)
- **Catalog:** Dynamic package variations (daily, weekly, monthly, 2-month tiers) with exact variation codes.

#### 3. Electricity Distribution Companies (Discos)

| Internal Key | VTPass Service ID | Distribution Company Name | Coverage Area |
|---|---|---|---|
| `ikedc` | `ikeja-electric` | Ikeja Electric | Lagos (Ikeja, Mainland) |
| `ekedc` | `eko-electric` | Eko Electricity Distribution | Lagos (Island, Lekki, Epe) |
| `aedc` | `abuja-electric` | Abuja Electricity Distribution | FCT, Niger, Kogi, Nasarawa |
| `bedc` | `benin-electric` | Benin Electricity Distribution | Edo, Delta, Ondo, Ekiti |
| `phed` | `portharcourt-electric` | Port Harcourt Electricity | Rivers, Bayelsa, Cross River, Akwa Ibom |
| `kaedco` | `kaduna-electric` | Kaduna Electric | Kaduna, Kebbi, Sokoto, Zamfara |
| `kedco` | `kano-electric` | Kano Electricity Distribution | Kano, Katsina, Jigawa |
| `eedc` | `enugu-electric` | Enugu Electricity Distribution | Enugu, Abia, Imo, Anambra, Ebonyi |
| `aba` | `aba-electric` | Aba Power Limited Electric | Aba Ring-fenced Area |

### Electricity Meter Verification & Token Delivery

Before accepting payment, Nova VTU executes an automated merchant verification handshake via `/api/merchant-verify`:
1. Sends `serviceID`, `billersCode` (meter number), and `type` (`prepaid`/`postpaid`) to VTPass.
2. Extracts and displays the registered customer name and installation address to avoid erroneous payments.
3. Upon successful prepaid token purchase, parses the generated alphanumeric token from the provider response and stores it directly on the `Transaction` record for immediate receipt rendering and email dispatch.

---

## 💳 Financial Integrity & Wallet Mechanics

### Atomic Operations & Concurrency Locking

To prevent race conditions, balance double-spending, and negative balance states, all balance adjustments utilize database row locking within explicit database transactions:

```python
with db_transaction.atomic():
    wallet = Wallet.objects.select_for_update().get(user=user)
    if wallet.balance < amount:
        raise InsufficientBalanceError("Insufficient wallet balance.")
    
    wallet.balance -= amount
    wallet.save()
    
    # Record transaction ledger
    transaction = Transaction.objects.create(
        wallet=wallet,
        transaction_type="purchase",
        amount=amount,
        status="completed"
    )
```

### Financial Boundary Invariants

- **Minimum Wallet Deposit:** `₦100.00`
- **Maximum Single Transaction Limit:** `₦100,000.00`
- **Maximum Wallet Balance Ceiling:** `₦1,000,000.00`
- **Precision:** Exact two decimal places (`Decimal("0.01")`) using Python `Decimal` to avoid floating-point drift.

---

## 🛡️ Security, Fraud Prevention & Rate Limiting

### Tiered Transaction Limits

Transactions are subjected to pre-execution fraud checks evaluated against user KYC status (`transactions/services/fraud_check.py`):

| Limit Rule | Unverified Users (Tier 1) | Verified Users (Tier 2 / KYC) |
|---|---|---|
| **Max Single Transaction** | ₦5,000 | ₦50,000 |
| **Max Daily Cumulative Total** | ₦20,000 | ₦200,000 |
| **Max Hourly Transaction Count** | 5 transactions / hour | 20 transactions / hour |

### Granular Rate Limiting

Configured via `django-ratelimit` and enforced by `config.middleware.RateLimitMiddleware`:

- **Authentication Endpoints (`/login/`):** `5 requests / minute`
- **Registration Endpoints (`/register/`):** `3 requests / minute`
- **Password Reset Requests (`/password_reset/`):** `3 requests / minute`
- **General API Queries:** `60 requests / minute`
- **Purchase Operations:** `10 requests / minute`
- **Webhook Receivers:** `100 requests / minute`

### Security Headers & Cookie Policies

When `DEBUG=False` in production:
- `SECURE_SSL_REDIRECT = True`
- `SECURE_HSTS_SECONDS = 3600` with subdomains and preload enabled
- `SESSION_COOKIE_SECURE = True` & `CSRF_COOKIE_SECURE = True`
- `X_FRAME_OPTIONS = 'DENY'`
- `SECURE_CONTENT_TYPE_NOSNIFF = True`

### Exception Hierarchy

Nova VTU implements domain-specific exceptions for deterministic error isolation:
- `InsufficientBalanceError` - Attempted purchase exceeds available wallet balance.
- `FraudCheckError` - Transaction violated velocity or amount tier boundaries.
- `InvalidNetworkError` - Supplied network or disco code is not supported.
- `MeterVerificationError` - Meter validation failed at the provider gateway.
- `VTPassError` - Upstream communication or fulfillment failure from VTPass.

---

## ⚙️ Management Commands & CLI Utilities

### Pending Transaction Re-checker (`recheck_pending_vtu`)

Automatically polls VTPass for transactions stuck in `pending` status, reconciles their final state, and refunds user wallets if transactions failed upstream:

```bash
# Recheck transactions pending for more than 10 minutes (default)
python manage.py recheck_pending_vtu

# Specify custom age threshold in minutes
python manage.py recheck_pending_vtu --max-age 30
```

#### Production Scheduling
Set up a cron job or Cloud Scheduler task to run every 5 to 15 minutes:
```cron
*/10 * * * * cd /app && python manage.py recheck_pending_vtu >> /var/log/vtu_recheck.log 2>&1
```

---

## 💾 Database Backup & Disaster Recovery

### Automated Compressed Backups (`backup.sh`)

Automated database dumping with `pg_dump`, gzip compression, retention pruning, and optional AWS S3 sync:

```bash
# Execute local database backup
./scripts/backup/backup.sh

# Create backup and upload to AWS S3 (Standard-IA)
./scripts/backup/backup.sh --upload

# Enforce a custom retention policy (e.g. 30 days)
./scripts/backup/backup.sh --retention 30
```

### Safe Database Restores (`restore.sh`)

Performs atomic database restoration inside a single transaction with pre-execution safety confirmations:

```bash
# Restore specific local archive
./scripts/backup/restore.sh /backups/nova_vtu_20250101_120000.sql.gz

# Restore latest available local backup
./scripts/backup/restore.sh --latest

# Fetch archive from S3 and restore
./scripts/backup/restore.sh --from-s3 nova_vtu_20250101_120000.sql.gz

# Dry-run inspection without applying changes
./scripts/backup/restore.sh --dry-run /backups/nova_vtu_latest.sql.gz
```

---

## 🐳 Docker & Container Orchestration

### Service Architecture

The `docker-compose.yml` orchestrates the complete production environment:
1. **`web`:** Django application running with Gunicorn (`Dockerfile` multi-stage build).
2. **`db`:** PostgreSQL 16 Alpine container with persistent volume mounts.
3. **`redis`:** Redis 7 Alpine caching and rate limiting engine.
4. **`nginx`:** Nginx reverse proxy routing traffic, serving static/media assets, and terminating SSL.
5. **`certbot`:** Automated Let's Encrypt SSL certificate issuance and 12-hour renewal daemon.
6. **`backup`:** Scheduled background database backup container.

### Docker Compose Workflows

```bash
# Start development stack
docker-compose up -d

# Start production stack with backup profile
docker-compose --profile backup up -d

# View application logs
docker-compose logs -f web

# Execute database migrations inside the container
docker-compose exec web python manage.py migrate

# Create superuser in Docker
docker-compose exec web python manage.py createsuperuser
```

---

## 🚢 Deployment Guides

### 1. Google Cloud Run + Neon PostgreSQL (Recommended)

Nova VTU is optimized for serverless container deployment on Google Cloud Run with serverless PostgreSQL (e.g., Neon or Supabase).

Detailed step-by-step instructions:
- 📖 **Quick Deployment Guide:** [docs/DEPLOY.md](docs/DEPLOY.md)
- 📘 **Complete GCP & CI/CD Guide:** [docs/GCP_DEPLOYMENT_GUIDE.md](docs/GCP_DEPLOYMENT_GUIDE.md)

#### Quick Deploy Summary:
```bash
# 1. Build and push container to Google Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/nova-vtu

# 2. Deploy Cloud Run service with secrets injection
gcloud run deploy nova-vtu \
  --image gcr.io/$PROJECT_ID/nova-vtu \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --set-env-vars "DEBUG=False" \
  --set-secrets "SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest,PAYSTACK_SECRET_KEY=paystack-secret-key:latest,PAYSTACK_PUBLIC_KEY=paystack-public-key:latest,VTPASS_API_KEY=vtpass-api-key:latest,VTPASS_SECRET_KEY=vtpass-secret-key:latest,RESEND_API_KEY=resend-api-key:latest"

# 3. Run database migrations via Cloud Run Job
gcloud run jobs create migrate \
  --image gcr.io/$PROJECT_ID/nova-vtu \
  --region us-central1 \
  --set-secrets "SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest" \
  --command "python,manage.py,migrate"
gcloud run jobs execute migrate --region us-central1
```

### 2. Multi-Container Docker Stack
Use `docker-compose.yml` with Nginx and Certbot for self-hosted Linux instances.

### 3. Traditional VPS (Nginx + Gunicorn + Systemd)
Deploy behind Nginx using the virtual host configuration provided in `nginx/conf.d/nova-vtu.conf`, running Gunicorn as a managed systemd service.

---

## 🧪 Testing & Quality Assurance

Nova VTU includes test coverage covering user onboarding, authentication state invariants, protected route access guards, and transaction flows.

### Running Test Suite

```bash
# Run all tests with python manage.py
SECRET_KEY=test-secret-key python manage.py test

# Or using uv
SECRET_KEY=test-secret-key uv run python manage.py test

# Or using virtual environment Python directly
SECRET_KEY=test-secret-key .venv/bin/python manage.py test

# Run tests for a specific app
SECRET_KEY=test-secret-key python manage.py test accounts
SECRET_KEY=test-secret-key python manage.py test transactions
SECRET_KEY=test-secret-key python manage.py test wallet

# Run tests with verbose output
SECRET_KEY=test-secret-key python manage.py test -v 2

# Run a specific test class
SECRET_KEY=test-secret-key python manage.py test accounts.tests.RegistrationTests

# Stop execution on first test failure
SECRET_KEY=test-secret-key python manage.py test --failfast
```

### Test Isolation Architecture
- When running in test mode (`sys.argv` contains `"test"`), Django automatically switches `DATABASES['default']` to an in-memory SQLite database (`:memory:`) for test speed and hermetic isolation.
- Rate limiting is automatically bypassed (`RATELIMIT_ENABLE = False`) during test runs.
- Email dispatch routes to Django's in-memory `locmem` backend (`EmailBackend`).

---

## DSH Temporal Smoke Test

This repository can be used to verify the DSH automated builder pipeline. It serves as a reliable reference target for validating automated build and execution workflows across temporal runs.

---

## 🔧 Troubleshooting & FAQ

### Q: Why do I get `django.core.exceptions.ImproperlyConfigured: SECRET_KEY environment variable is required`?
**A:** Ensure your `.env` file exists and contains a valid `SECRET_KEY`. When executing tests or CLI scripts directly, pass `SECRET_KEY=your-key` in the shell environment.

### Q: How can I test Paystack webhooks on local development?
**A:** Use `ngrok` to expose your local server:
```bash
ngrok http 8000
```
Add your ngrok forwarding domain to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in `.env`, then configure your webhook URL in Paystack Dashboard to `https://<your-ngrok-id>.ngrok-free.app/wallet/webhook/`.

### Q: Why do static files fail to load in production?
**A:** In production (`DEBUG=False`), static assets are served through Whitenoise with compressed manifest hashing. Ensure you run:
```bash
python manage.py collectstatic --no-input
```
prior to starting Gunicorn.

---

## 🤝 Contributing

We welcome contributions to Nova VTU! Follow these steps:

1. **Fork the Repository**
2. **Create a Feature Branch:**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Adhere to Code Standards:**
   - Follow PEP 8 guidelines and include explicit type hints.
   - Maintain defensive error handling and concurrency row locks for financial operations.
   - Add unit tests for all new views and services.
4. **Run Verification Tests:**
   ```bash
   SECRET_KEY=test-key python manage.py test
   ```
5. **Commit with Conventional Messages:**
   ```bash
   git commit -m "feat(transactions): add support for postpaid meter verification"
   ```
6. **Open a Pull Request**

---

## 📝 License

This project is open-source software licensed under the [MIT License](LICENSE).

---

## 🗺️ Roadmap

- [x] Comprehensive authentication & user profile management
- [x] Atomic wallet system with Paystack funding integration
- [x] Airtime purchase for MTN, Airtel, GLO, and 9mobile
- [x] Data bundle catalog and purchase integration
- [x] Prepaid electricity payment with instant meter validation & token delivery
- [x] Transaction audit trail & downloadable HTML receipts
- [x] Automated transaction status reconciler (`recheck_pending_vtu`)
- [x] Multi-tier fraud detection & velocity throttling
- [x] Multi-container Docker & Nginx SSL setup
- [ ] Tier 2 KYC identity document verification upload
- [ ] Cable TV subscriptions (DSTV, GOTV, Startimes, Showmax)
- [ ] Automated wallet payout / withdrawal system
- [ ] Developer REST API with personal API token authentication
- [ ] React Native cross-platform mobile application

---

<div align="center">

**Built with ❤️ for reliable digital commerce in Nigeria.**

</div>
