<div align="center">

# 🚀 Nova VTU

### Virtual Top-Up Platform for Nigeria

*Buy airtime, data bundles, and pay electricity bills seamlessly*

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-MVP-orange?style=for-the-badge)]()

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [API Integration](#-api-integrations) • [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Environment Setup](#-environment-setup)
- [Project Structure](#-project-structure)
- [API Integrations](#-api-integrations)
- [Usage Guide](#-usage-guide)
- [Security & Fraud Prevention](#-security--fraud-prevention)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

**Nova VTU** is a modern Django-based Virtual Top-Up platform designed for the Nigerian market. It provides a secure, user-friendly interface for purchasing digital services including airtime, data bundles, and electricity bill payments.

### Why Nova VTU?

- ✅ **Secure Payments** - Integrated with Paystack for safe transactions
- ✅ **Instant Processing** - Real-time VTU service delivery via VTPass
- ✅ **Fraud Protection** - Built-in transaction limits and verification
- ✅ **Email Notifications** - Automated receipts and confirmations
- ✅ **Modern UI** - Clean, responsive design with Tailwind CSS
- ✅ **Admin Dashboard** - Comprehensive management with Django Unfold

---

## ✨ Features

### Core Functionality

| Feature | Description |
|---------|-------------|
| 🔐 **User Authentication** | Secure registration, login, password reset with email verification |
| 💳 **Wallet System** | Fund wallet via Paystack, track balance in real-time |
| 📱 **Airtime Purchase** | Buy airtime for MTN, Airtel, GLO, 9mobile |
| 📊 **Data Bundles** | Purchase data plans from all major Nigerian networks |
| ⚡ **Electricity Bills** | Pay PREPAID electricity bills with instant token delivery |
| 📜 **Transaction History** | View, filter, and download transaction receipts |
| 👤 **Profile Management** | Update profile info, upload avatar, manage account |
| 📧 **Email Notifications** | Automated confirmations for purchases and wallet funding |
| 🛡️ **Fraud Detection** | Transaction limits based on user verification status |

### Admin Features

- 📊 Modern admin dashboard powered by Django Unfold
- 🔍 Manual transaction recheck for pending transactions
- ⚙️ Maintenance mode toggle
- 📈 Transaction monitoring and management
- 🚨 Fraud prevention controls

---

## 🛠️ Tech Stack

### Backend
- **Framework:** Django 6.0+
- **Language:** Python 3.13+
- **Database:** SQLite3 (Development) / PostgreSQL (Production)
- **Payment Gateway:** Paystack
- **VTU Provider:** VTPass

### Frontend
- **CSS Framework:** Tailwind CSS
- **Templates:** Django Templates
- **Icons:** Heroicons / Font Awesome

### Key Dependencies
```
django>=6.0
django-unfold>=0.73.1         # Modern admin UI
django-ratelimit>=4.1.0       # API rate limiting
httpx>=0.28.0                 # HTTP client for API calls
paystack>=1.5.0               # Paystack integration
pillow>=12.0.0                # Image processing
python-dotenv>=1.2.1          # Environment management
whitenoise>=6.8.2             # Static file serving
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13 or higher
- pip or uv package manager
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/dreww01/VTU.git
cd nova-vtu
```

2. **Create and activate virtual environment**
```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
# Using pip
pip install -r pyproject.toml

# Or using uv (recommended)
uv sync
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys (see Environment Setup section)
```

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create a superuser**
```bash
python manage.py createsuperuser
```

7. **Run the development server**
```bash
python manage.py runserver
```

8. **Access the application**
- Frontend: http://127.0.0.1:8000
- Admin: http://127.0.0.1:8000/admin
- Dashboard: http://127.0.0.1:8000/dashboard (after login)

---

## 🔐 Environment Setup

Create a `.env` file in the project root with the following variables:

### Django Settings
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

> 💡 **Generate Secret Key:** `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

### Paystack Configuration
Sign up at [Paystack](https://dashboard.paystack.com) and get your API keys:

```env
PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx
PAYSTACK_PUBLIC_KEY=pk_test_xxxxxxxxxxxxxxxxxxxx
```

### VTPass Configuration
Register at [VTPass](https://vtpass.com) for VTU services:

```env
VTPASS_BASE_URL=https://sandbox.vtpass.com/api
VTPASS_API_KEY=your_api_key
VTPASS_SECRET_KEY=SK_your_secret_key
VTPASS_PUBLIC_KEY=PK_your_public_key
```

### Email Configuration (Resend)
Get API key from [Resend](https://resend.com):

```env
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
DEFAULT_FROM_EMAIL=Nova VTU <noreply@yourdomain.com>
```

### Optional: Database (Production)
For production, use PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@host:5432/nova_vtu?sslmode=require
```

---

## 📁 Project Structure

```
VTU/
├── accounts/                   # User authentication & profiles
│   ├── migrations/
│   ├── models.py              # UserProfile model
│   ├── views.py               # Auth views (login, register, profile)
│   ├── urls.py
│   └── signals.py             # Auto-create profile on user registration
│
├── wallet/                     # Wallet & payment system
│   ├── migrations/
│   ├── models.py              # Wallet model
│   ├── views.py               # Fund, verify, webhook handlers
│   └── urls.py
│
├── transactions/               # VTU services
│   ├── migrations/
│   ├── models.py              # Transaction, AppSettings models
│   ├── views.py               # Service purchase views
│   ├── urls.py
│   ├── admin.py               # Admin configuration
│   ├── providers/             # External API integrations
│   │   ├── __init__.py
│   │   ├── vtpass.py          # VTPass API client
│   │   └── exceptions.py      # Custom exceptions
│   └── services/              # Business logic
│       ├── airtime.py         # Airtime purchase logic
│       ├── data.py            # Data bundle logic
│       ├── electricity.py     # Electricity payment logic
│       ├── fraud_check.py     # Fraud prevention
│       └── verification.py    # Meter/service verification
│
├── config/                     # Project settings
│   ├── settings.py            # Django settings
│   ├── urls.py                # URL routing
│   ├── wsgi.py
│   └── middleware.py          # Custom middleware
│
├── templates/                  # HTML templates
│   ├── accounts/              # Auth templates
│   ├── wallet/                # Wallet templates
│   ├── transactions/          # Transaction templates
│   ├── emails/                # Email templates
│   ├── errors/                # Error pages (404, 500, 429)
│   └── layout.html            # Base template
│
├── media/                      # User-uploaded files
│   └── avatars/               # Profile pictures
│
├── static/                     # Static assets (CSS, JS, images)
│
├── scripts/                    # Utility scripts
│   └── backup/                # Database backup/restore scripts
│
├── .env.example               # Environment template
├── .gitignore
├── pyproject.toml             # Project dependencies
├── manage.py                  # Django management script
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Docker Compose setup
├── DEPLOYMENT.md              # Deployment guide
└── README.md                  # This file
```

---

## 🔌 API Integrations

### Paystack Payment Gateway

**Purpose:** Secure wallet funding

**Flow:**
1. User initiates wallet funding
2. Paystack payment page opens
3. User completes payment
4. Webhook verifies transaction
5. Wallet credited automatically

**Endpoints Used:**
- Initialize Transaction: `/transaction/initialize`
- Verify Transaction: `/transaction/verify/:reference`
- Webhook: `/paystack/webhook/` (receives payment notifications)

### VTPass VTU Provider

**Purpose:** Airtime, data, and electricity services

**Services Implemented:**

| Service | Service ID | Networks/Providers |
|---------|-----------|-------------------|
| Airtime | `mtn`, `airtel`, `glo`, `etisalat` | All Nigerian networks |
| Data | `mtn-data`, `airtel-data`, `glo-data`, `etisalat-data` | All Nigerian networks |
| Electricity | `ikeja-electric`, `eko-electric`, `abuja-electric`, etc. | PREPAID meters only |

**API Endpoints:**
- Service verification: `/api/service-variations`
- Purchase: `/api/pay`
- Verify meter number: `/api/merchant-verify`

---

## 📖 Usage Guide

### For Users

#### 1. Register an Account
- Navigate to `/register`
- Fill in username, email, password
- Verify email (check spam folder)
- Login at `/login`

#### 2. Fund Your Wallet
- Go to Dashboard → Wallet
- Click "Fund Wallet"
- Enter amount (minimum ₦100)
- Complete payment via Paystack
- Wallet credited automatically

#### 3. Purchase Services

**Airtime:**
1. Dashboard → Buy Airtime
2. Select network (MTN, Airtel, GLO, 9mobile)
3. Enter phone number and amount
4. Confirm purchase
5. Receive confirmation email

**Data:**
1. Dashboard → Buy Data
2. Select network
3. Choose data plan from dropdown
4. Enter phone number
5. Confirm purchase

**Electricity:**
1. Dashboard → Pay Electricity
2. Select provider (e.g., Ikeja Electric)
3. Enter meter number
4. System verifies meter details
5. Enter amount
6. Receive token via email and on-screen

#### 4. View Transaction History
- Dashboard → Transaction History
- Filter by date or type
- Download receipts (PDF/Email)

### For Administrators

#### Access Admin Panel
- Navigate to `/admin`
- Login with superuser credentials

#### Manage Transactions
- View all transactions
- Manually recheck pending transactions
- Update transaction statuses
- View fraud alerts

#### System Settings
- Toggle fraud checks on/off
- Enable/disable maintenance mode
- Monitor user activity

---

## 🛡️ Security & Fraud Prevention

### Transaction Limits

**Unverified Users** (default):
- Single transaction: ₦5,000
- Daily limit: ₦20,000
- Hourly limit: 5 transactions

**Verified Users** (future KYC):
- Single transaction: ₦50,000
- Daily limit: ₦200,000
- Hourly limit: 20 transactions

### Security Features

- ✅ Atomic wallet transactions (prevents race conditions)
- ✅ Database row locking during wallet operations
- ✅ Paystack webhook signature verification
- ✅ Rate limiting on API endpoints
- ✅ CSRF protection
- ✅ Password hashing (Django's built-in)
- ✅ HTTPS enforcement in production
- ✅ Secure session management

### Error Handling

Custom exceptions for better error tracking:
- `InsufficientBalanceError` - Wallet balance too low
- `FraudCheckError` - Transaction exceeds limits
- `MeterVerificationError` - Invalid meter number
- `VTPassError` - VTU provider API errors

---

## 🚢 Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in production
- [ ] Generate new `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up PostgreSQL database
- [ ] Use production Paystack/VTPass keys
- [ ] Configure HTTPS/SSL
- [ ] Set up email service (Resend/Gmail)
- [ ] Configure static files with Whitenoise
- [ ] Set up backup scripts
- [ ] Enable logging and monitoring

### Deployment Options

#### 1. **Google Cloud Platform (Recommended)**
Complete guides available in [.claude/deployment/](.claude/deployment/):
- **[Quick Start](.claude/deployment/quick-start.md)** - Deploy in 30 minutes with step-by-step commands
- **[Full Guide](.claude/deployment/gcp-deployment.md)** - Comprehensive GCP deployment documentation
- **[Local Testing](.claude/deployment/local-testing.md)** - Test Docker setup before deployment

**Tech Stack:** Cloud Run + Cloud SQL (PostgreSQL) + Cloud Storage

**Cost:** ~$15-30/month for low-medium traffic

**Quick Deploy:**
```bash
# See .claude/deployment/quick-start.md for full commands
gcloud builds submit --tag gcr.io/PROJECT_ID/nova-vtu
gcloud run deploy nova-vtu --image gcr.io/PROJECT_ID/nova-vtu
```

#### 2. **Docker / Docker Compose**
```bash
# Local testing
docker-compose up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### 3. **Railway / Render**
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed Railway deployment guide.

#### 4. **Traditional VPS**
- Use Gunicorn/uWSGI
- Nginx reverse proxy
- Systemd service
- PostgreSQL database

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
   - Follow PEP 8 style guide
   - Add tests if applicable
   - Update documentation
4. **Commit your changes**
   ```bash
   git commit -m "Add: your feature description"
   ```
5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request**

### Code Style

- Follow Django best practices
- Use type hints where applicable
- Write descriptive commit messages
- Comment complex logic
- Keep functions small and focused

### Reporting Issues

Found a bug? Have a feature request?

1. Check existing issues first
2. Open a new issue with:
   - Clear title and description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Screenshots if applicable

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Django](https://www.djangoproject.com/) - Web framework
- [Paystack](https://paystack.com/) - Payment processing
- [VTPass](https://vtpass.com/) - VTU services
- [Django Unfold](https://github.com/unfoldadmin/django-unfold) - Admin UI
- [Tailwind CSS](https://tailwindcss.com/) - Styling

---

## 📞 Support

- **Documentation:** [Project Wiki](#)
- **Email:** support@novavtu.com
- **Issues:** [GitHub Issues](https://github.com/dreww01/VTU/issues)

---

## DSH Temporal Smoke Test

This repository can be used to verify the DSH automated builder pipeline. It serves as an end-to-end test case for automated build and verification workflows.

---

## 🗺️ Roadmap

### Current (MVP)
- ✅ User authentication
- ✅ Wallet system
- ✅ Airtime purchase
- ✅ Data bundles
- ✅ Electricity bills (PREPAID)
- ✅ Transaction history
- ✅ Email notifications

### Planned Features
- [ ] KYC verification system
- [ ] Wallet withdrawal
- [ ] TV subscription (DSTV, GOTV, Startimes)
- [ ] Mobile app (React Native)
- [ ] Referral/bonus system
- [ ] API for developers
- [ ] Multi-currency support
- [ ] Bill reminders
- [ ] POSTPAID electricity support

---

<div align="center">

**Made with ❤️ for Nigeria**

⭐ Star this repo if you find it helpful!

[Report Bug](https://github.com/dreww01/VTU/issues) • [Request Feature](https://github.com/dreww01/VTU/issues)

</div>
