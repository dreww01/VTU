<div align="center">

# 🚀 Nova VTU

### Virtual Top-Up Platform for Nigeria

*Buy airtime, data bundles, and pay electricity bills seamlessly*

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-MVP-orange?style=for-the-badge)]()

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture--design-patterns) • [API Map](#-api--url-routing-reference) • [Management Commands](#-management-commands--cli-tools) • [Testing](#-testing--quality-assurance) • [Deployment](#-deployment)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack & Dependencies](#-tech-stack--dependencies)
- [Architecture & Design Patterns](#-architecture--design-patterns)
- [Quick Start](#-quick-start)
- [Environment Configuration](#-environment-configuration)
- [API & URL Routing Reference](#-api--url-routing-reference)
- [Project Structure](#-project-structure)
- [API Integrations](#-api-integrations)
- [Management Commands & CLI Tools](#-management-commands--cli-tools)
- [Security & Fraud Prevention](#-security--fraud-prevention)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

**Nova VTU** is an enterprise-ready, Django-based Virtual Top-Up platform engineered for the Nigerian telecom and utility landscape. It enables end-users to fund their wallets and purchase digital services—including instant airtime, mobile data subscriptions, and prepaid electricity tokens—while enforcing strict transactional safety, rate limiting, and fraud prevention.

### Key Highlights

- 💳 **Seamless Wallet System** – Fund wallet via Paystack checkout with instant credit upon webhook verification.
- ⚡ **Instant Multi-Provider Top-Ups** – Real-time VTU fulfillment through VTPass (MTN, Airtel, GLO, 9mobile, Ikeja, Eko, Abuja, etc.).
- 🔒 **Defensive Financial Integrity** – Atomic transactions (`select_for_update`), strict decimal quantization, and balance invariants prevent race conditions and overdrafts.
- 🛡️ **Tiered Fraud & Abuse Protection** – Built-in single-transaction, daily volume, and hourly frequency limits with bypass controls.
- 📧 **Automated Transaction Notifications** – HTML receipts and status alerts delivered via email.
- 📊 **Tailwind & Unfold Admin UI** – Clean user interface styled with Tailwind CSS, backed by a modern Django Unfold administrative control plane.
- 🔄 **Automated Recheck Subsystem** – Built-in management command to reconcile pending provider transactions automatically.

---

## ✨ Features

### Core User Functionality

| Feature | Details |
|---------|---------|
| 🔐 **User Authentication** | Custom authentication workflows: registration with field validation, login, session logout, password reset code generation, and confirmation. |
| 💳 **Digital Wallet** | In-app wallet management with Paystack payment gateway integration, transaction logs, and real-time balance tracking. |
| 📱 **Airtime Purchase** | Instant airtime top-ups for MTN, Airtel, GLO, and 9mobile with defensive network validation. |
| 📊 **Data Bundles** | Live data plan variations retrieval and top-up across all Nigerian networks. |
| ⚡ **Electricity Bill Payment** | Prepaid electricity token generation for DISCOs (Ikeja, Eko, Abuja, Kano, Port Harcourt, etc.) with meter number pre-verification. |
| 📜 **Transaction History & Receipts** | Filterable transaction records with unique reference IDs, formatted receipts, and delivery token displays. |
| 👤 **User Profiles** | Profile management with full name, avatar upload with validation, and contact details. |

### Administrative & Operational Features

- 🎛️ **Django Unfold Dashboard** – Visual admin interface for monitoring user accounts, wallet balances, and transaction states.
- 🔍 **Transaction Requery Subsystem** – Provider reconciliation for pending or delayed VTU operations.
- ⚙️ **Dynamic AppSettings** – Live toggle for maintenance mode and fraud checks without requiring code deployments.
- 📈 **Detailed Audit Logs** – Raw provider payload persistence (`provider_response`), retry counters (`requery_attempts`), and manual review flags.

---

## 🛠️ Tech Stack & Dependencies

### Backend & Frameworks
- **Framework:** Django 6.0+
- **Language:** Python 3.13+
- **Database:** SQLite (Development) / PostgreSQL (Production, e.g., Neon / Cloud SQL)
- **Payment Processing:** Paystack API
- **VTU Gateway:** VTPass REST API
- **Email Delivery:** Resend API / SMTP backend

### Frontend & Styling
- **CSS Framework:** Tailwind CSS
- **Templating:** Django Template Language (DTL)
- **Icons:** Heroicons / Font Awesome

### Dependency Specifications

```toml
[dependencies]
django = ">=6.0"
django-unfold = ">=0.73.1"      # Modern, customizable Django admin interface
django-ratelimit = ">=4.1.0"    # Decorator-based view rate limiting
httpx = ">=0.28.0"              # Asynchronous and synchronous HTTP client
paystack = ">=1.5.0"            # Paystack Python SDK
pillow = ">=12.0.0"             # Image handling and avatar validation
python-dotenv = ">=1.2.1"       # Twelve-factor environment variable loading
whitenoise = ">=6.8.2"          # Optimized static asset serving
```

---

## 🏛️ Architecture & Design Patterns

### 1. Atomic Wallet Transactions & Balance Invariants
All financial operations enforce strict ACID compliance using Django's `transaction.atomic()` context managers and row-level database locking:
```python
# Atomic debit pattern
with transaction.atomic():
    wallet = Wallet.objects.select_for_update().get(user=user)
    if wallet.balance < amount:
        raise InsufficientBalanceError("Insufficient wallet balance.")
    wallet.balance -= amount
    wallet.save()
    Transaction.objects.create(wallet=wallet, transaction_type="purchase", ...)
```

### 2. Transaction Lifecycle & State Machine
```
[User Initiates Top-Up]
       │
       ▼
[Fraud Limit Check] ──(Exceeded)──► [Block & Prompt User]
       │ (Passed)
       ▼
[Atomic Balance Debit]
       │
       ▼
[VTPass API Request]
   ├── Success (Delivered) ──► [Status: Completed] ──► [Send Email Receipt]
   ├── Failed (Provider)   ──► [Refund Wallet] ──► [Status: Failed]
   └── Pending / Timeout   ──► [Status: Pending] ──► [Queue Requery Task]
                                                         │
                                                         ▼
                                             [recheck_pending_vtu CLI]
```

### 3. Graceful Rate Limiting Middleware
The custom `RateLimitMiddleware` interceptor catches `Ratelimited` exceptions thrown by view decorators and dispatches appropriate responses:
- **API/JSON Clients:** Returns `429 Too Many Requests` with `{"error": "rate_limit_exceeded", "message": "..."}`.
- **Web Browsers:** Renders `templates/errors/429.html` accompanied by a `Retry-After: 60` HTTP header.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.13 or higher
- `uv` (recommended) or `pip`
- Git

### Installation & Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/dreww01/VTU.git
   cd VTU
   ```

2. **Create and activate a virtual environment**
   ```bash
   # Using uv
   uv venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

   # Or using standard venv
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install project dependencies**
   ```bash
   # Using uv
   uv sync

   # Or using pip
   pip install -e .
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and supply your SECRET_KEY and API credentials
   ```

5. **Execute database migrations**
   ```bash
   SECRET_KEY=dev-secret-key python manage.py migrate
   ```

6. **Create an administrative user**
   ```bash
   SECRET_KEY=dev-secret-key python manage.py createsuperuser
   ```

7. **Start the local development server**
   ```bash
   SECRET_KEY=dev-secret-key python manage.py runserver
   ```

8. **Access the application**
   - User Dashboard: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - Admin Panel: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
   - Health Check: [http://127.0.0.1:8000/health/](http://127.0.0.1:8000/health/)

---

## 🔐 Environment Configuration

The application is configured using environment variables loaded via `python-dotenv`. Create a `.env` file in the project root:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** | — | Django cryptographic secret key. |
| `DEBUG` | No | `False` | Enable/disable debug mode (set to `False` in production). |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-delimited host/domain names allowed to serve the app. |
| `CSRF_TRUSTED_ORIGINS` | No | `http://localhost:8000` | Comma-delimited trusted origins for CSRF protection. |
| `DATABASE_URL` | No | SQLite | PostgreSQL database URL (`postgresql://user:pass@host:5432/dbname?sslmode=require`). |
| `PAYSTACK_SECRET_KEY` | **Yes** | — | Paystack secret key (`sk_test_...` or `sk_live_...`). |
| `PAYSTACK_PUBLIC_KEY` | **Yes** | — | Paystack public key (`pk_test_...` or `pk_live_...`). |
| `VTPASS_BASE_URL` | No | `https://sandbox.vtpass.com/api` | VTPass endpoint (`https://api-service.vtpass.com/api` for live). |
| `VTPASS_API_KEY` | **Yes** | — | VTPass API Key. |
| `VTPASS_SECRET_KEY` | **Yes** | — | VTPass Secret Key (`SK_...`). |
| `VTPASS_PUBLIC_KEY` | **Yes** | — | VTPass Public Key (`PK_...`). |
| `RESEND_API_KEY` | No | — | Resend API key for transactional emails. |
| `DEFAULT_FROM_EMAIL` | No | `Nova VTU <noreply@novavtu.com>` | Sender address for outgoing system emails. |

---

## 🗺️ API & URL Routing Reference

### Authentication & Accounts (`/`)
| Endpoint | View | Method | Description |
|----------|------|--------|-------------|
| `/` | `dashboard_view` | `GET` | User dashboard displaying balance and quick action cards. |
| `/login/` | `login_view` | `GET`, `POST` | User authentication login page with rate limiting. |
| `/register/` | `register_view` | `GET`, `POST` | New user account registration. |
| `/logout/` | `logout_view` | `POST`, `GET` | Session invalidation and logout. |
| `/account/profile/` | `profile_view` | `GET`, `POST` | User profile overview and avatar photo upload. |
| `/password_reset/` | `send_reset_code` | `GET`, `POST` | Request password reset code via email. |
| `/password_reset_confirm/` | `password_reset_confirm` | `GET`, `POST` | Verify reset code and set new password. |
| `/services/` | `vtu_services_view` | `GET` | VTU services navigation hub. |

### Wallet Management (`/wallet/`)
| Endpoint | View | Method | Description |
|----------|------|--------|-------------|
| `/wallet/info/` | `wallet_info` | `GET` | Balance summary and recent wallet activity. |
| `/wallet/fund/` | `fund_wallet` | `GET`, `POST` | Initialize Paystack deposit transaction. |
| `/wallet/verify/<reference>/` | `verify_payment` | `GET` | Callback verification for completed Paystack payments. |
| `/wallet/webhook/` | `paystack_webhook` | `POST` | Paystack webhook receiver with signature validation. |

### VTU Transactions (`/transactions/`)
| Endpoint | View | Method | Description |
|----------|------|--------|-------------|
| `/transactions/history/` | `transaction_history` | `GET` | Full transaction audit trail with status filters. |
| `/transactions/airtime/buy/` | `buy_airtime` | `GET`, `POST` | Airtime purchase interface and execution. |
| `/transactions/data/buy/` | `buy_data` | `GET`, `POST` | Data bundle selection and purchase. |
| `/transactions/electricity/buy/`| `pay_electricity` | `GET`, `POST` | Prepaid meter verification and bill payment. |
| `/transactions/airtime/receipt/<ref>/` | `airtime_receipt` | `GET` | Airtime purchase receipt view. |
| `/transactions/data/receipt/<ref>/` | `data_receipt` | `GET` | Data bundle purchase receipt view. |
| `/transactions/electricity/receipt/<ref>/` | `electricity_receipt`| `GET` | Electricity token and transaction receipt. |
| `/transactions/webhook/vtpass/` | `vtpass_webhook` | `POST` | VTPass asynchronous transaction status webhook. |

### Health Checks (`/health/`)
| Endpoint | View | Method | Description |
|----------|------|--------|-------------|
| `/health/` | `health_check` | `GET` | Returns `{"status": "healthy"}` for load balancers and orchestrators. |

---

## 📁 Project Structure

```
VTU/
├── accounts/                   # User authentication, profiles, and dashboard
│   ├── forms.py               # Registration, profile, and auth forms
│   ├── models.py              # UserProfile model
│   ├── signals.py             # Automatic UserProfile creation signal
│   ├── tests.py               # Accounts unit and integration tests
│   ├── urls.py                # Accounts URL routes
│   ├── validators.py          # Custom validation helpers (e.g. avatar validator)
│   └── views.py               # Authentication and profile views
│
├── wallet/                     # Wallet balances and payment processing
│   ├── models.py              # Wallet model with deposit/deduct operations
│   ├── tests.py               # Wallet balance and concurrency tests
│   ├── urls.py                # Wallet routes and webhook endpoints
│   └── views.py               # Fund, verify, and webhook handling
│
├── transactions/               # VTU service processing & business logic
│   ├── admin.py               # Django Unfold custom admin dashboards
│   ├── models.py              # Transaction & AppSettings models
│   ├── urls.py                # Service endpoints & receipts
│   ├── views.py               # Airtime, data, electricity purchase views
│   ├── providers/             # External integration layer
│   │   ├── exceptions.py      # Provider-specific exceptions
│   │   └── vtpass.py          # VTPass REST API client
│   ├── services/              # Core business domain logic
│   │   ├── airtime.py         # Airtime validation & execution
│   │   ├── data.py            # Data plans validation & execution
│   │   ├── electricity.py     # Meter verification & token dispatch
│   │   ├── fraud_check.py     # Velocity and volume limit evaluations
│   │   ├── verification.py    # Merchant/meter verification & requery engine
│   │   └── vtu_service.py     # Base VTU service execution framework
│   └── management/commands/   # Custom management commands
│       └── recheck_pending_vtu.py # Background pending transaction reconciler
│
├── config/                     # Django core settings & routing
│   ├── asgi.py                # ASGI configuration
│   ├── middleware.py          # RateLimitMiddleware & error handlers
│   ├── settings.py            # Project configuration & third-party setup
│   ├── urls.py                # Root URL dispatcher
│   └── wsgi.py                # WSGI configuration
│
├── docs/                       # Project technical documentation
│   ├── DEPLOY.md              # Cloud Run & Neon PostgreSQL deployment guide
│   └── GCP_DEPLOYMENT_GUIDE.md# Extended Google Cloud architecture guide
│
├── scripts/                    # Operational automation scripts
│   └── backup/
│       ├── backup.sh          # PostgreSQL dump script with S3 upload
│       └── restore.sh         # PostgreSQL database restoration script
│
├── templates/                  # Jinja/Django HTML templates
│   ├── accounts/              # Auth, dashboard, profile templates
│   ├── emails/                # Transaction receipts and notification emails
│   ├── errors/                # Custom 404, 500, and 429 error pages
│   ├── transactions/          # Service purchase forms and receipt views
│   └── wallet/                # Funding and transaction history views
│
├── Dockerfile                 # Multi-stage container definition
├── docker-compose.yml         # Local Docker composition setup
├── pyproject.toml             # Project build configuration & dependencies
└── manage.py                  # Django management CLI
```

---

## 🔌 API Integrations

### Paystack Payment Gateway
- **Flow:** User triggers a wallet top-up -> App initializes transaction with Paystack -> User completes payment on Paystack checkout -> Redirected to `/wallet/verify/<ref>/` -> Paystack triggers webhook to `/wallet/webhook/` -> Webhook verifies HMAC SHA512 signature and credits wallet atomically.
- **Reference:** [Paystack API Documentation](https://paystack.com/docs/api/)

### VTPass VTU Gateway
- **Supported Services:**
  - **Airtime:** MTN (`mtn`), Airtel (`airtel`), GLO (`glo`), 9mobile (`etisalat`).
  - **Data:** MTN Data (`mtn-data`), Airtel Data (`airtel-data`), GLO Data (`glo-data`), 9mobile Data (`etisalat-data`).
  - **Electricity (Prepaid):** Ikeja (`ikeja-electric`), Eko (`eko-electric`), Abuja (`abuja-electric`), Kano (`kano-electric`), etc.
- **Reference:** [VTPass Developer Portal](https://vtpass.com/documentation/)

---

## 🛠️ Management Commands & CLI Tools

### Recheck Pending Transactions
When external VTU provider calls experience timeouts or return pending status, this command reconciles and finalizes their statuses:

```bash
# Recheck all transactions pending for more than 10 minutes (default)
SECRET_KEY=dev-secret-key python manage.py recheck_pending_vtu

# Recheck transactions pending for more than 30 minutes
SECRET_KEY=dev-secret-key python manage.py recheck_pending_vtu --max-age 30
```

### Database Backup & Restore Automation
Located under `scripts/backup/`:

```bash
# Execute compressed PostgreSQL backup
./scripts/backup/backup.sh

# Create backup and upload to Amazon S3
./scripts/backup/backup.sh --upload --retention 30

# Restore database from backup archive
./scripts/backup/restore.sh /backups/nova_vtu_20250101_120000.sql.gz
```

---

## 🛡️ Security & Fraud Prevention

### Rate Limiting & Velocity Controls
- **Rate Limits:** Enforced via `django-ratelimit` on sensitive endpoints (e.g. login, registration, password reset, and transaction submissions).
- **Graceful Degradation:** Automatic translation to `429 Too Many Requests` responses with informative retry guidance.

### Transaction & Balance Rules
- **Maximum Transaction Limit:** ₦100,000 per single operation.
- **Maximum Wallet Balance:** ₦1,000,000 ceiling.
- **Precision:** `Decimal` type with fixed 2-place quantize (`0.01`) preventing floating-point inaccuracies.

### User Tier Transaction Limits
| Tier | Single Transaction Limit | Daily Limit | Hourly Velocity |
|------|--------------------------|-------------|-----------------|
| **Standard / Unverified** | ₦5,000 | ₦20,000 | 5 transactions / hr |
| **Verified (KYC)** | ₦50,000 | ₦200,000 | 20 transactions / hr |

---

## 🧪 Testing & Quality Assurance

Nova VTU includes test suites verifying authentication workflows, wallet debit/credit invariants, fraud detection policies, and service purchase handlers.

### Running the Test Suite

```bash
# Run all tests
SECRET_KEY=test python manage.py test

# Run accounts tests
SECRET_KEY=test python manage.py test accounts

# Run transactions and services tests
SECRET_KEY=test python manage.py test transactions
```

---

## 🚢 Deployment

### Production Checklist
- [ ] Set `DEBUG=False` in production environment.
- [ ] Configure unique, strong `SECRET_KEY`.
- [ ] Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- [ ] Attach managed PostgreSQL instance (`DATABASE_URL`).
- [ ] Configure live Paystack and VTPass API keys.
- [ ] Ensure Whitenoise collects static files (`python manage.py collectstatic --noinput`).
- [ ] Configure SSL termination and reverse proxy (Nginx or Cloud Run ingress).

### Deployment Guides
Detailed infrastructure setup guides are available in the repository:
- **[GCP Cloud Run & Neon Guide](docs/DEPLOY.md)** – Step-by-step setup using Google Cloud Run, Secret Manager, and Neon PostgreSQL.
- **[Extended GCP Architecture](docs/GCP_DEPLOYMENT_GUIDE.md)** – Comprehensive cloud deployment architecture.

### Running with Docker Compose

```bash
# Build and run containers locally
docker-compose up --build -d

# View service logs
docker-compose logs -f
```

---

## 🤝 Contributing

Contributions are welcome! Please adhere to the following workflow:

1. Fork the repository.
2. Create your feature branch (`git checkout -b feat/my-feature`).
3. Write clean, defensive code adhering to PEP 8.
4. Verify all tests pass (`SECRET_KEY=test python manage.py test`).
5. Commit your changes with conventional commit messages (`git commit -m "feat: add feature"`).
6. Open a Pull Request.

---

## 📝 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Made with ❤️ for Nigeria**

⭐ Star this repository if you find it helpful!

</div>
