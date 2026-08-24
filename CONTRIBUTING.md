# Contributing to Nova VTU

Thank you for your interest in contributing to **Nova VTU**! We welcome contributions from developers of all skill levels. Whether you are fixing a bug, adding new features, improving documentation, or writing tests, your help is appreciated.

Please take a moment to review this document before submitting contributions.

---

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [How Can I Contribute?](#-how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Contributing Code](#contributing-code)
  - [Improving Documentation](#improving-documentation)
- [Development Environment Setup](#-development-environment-setup)
  - [Prerequisites](#prerequisites)
  - [Local Installation](#local-installation)
  - [Environment Configuration](#environment-configuration)
  - [Database & Superuser Setup](#database--superuser-setup)
- [Project Architecture & Structure](#-project-architecture--structure)
- [Development Workflow](#-development-workflow)
  - [Branch Naming](#branch-naming)
  - [Commit Message Guidelines](#commit-message-guidelines)
- [Coding Standards & Best Practices](#-coding-standards--best-practices)
  - [Python & Django Guidelines](#python--django-guidelines)
  - [Financial & Concurrency Safety](#financial--concurrency-safety)
  - [Security Best Practices](#security-best-practices)
- [Testing & Quality Assurance](#-testing--quality-assurance)
  - [Running Tests](#running-tests)
  - [Writing Tests](#writing-tests)
  - [Linting and Formatting](#linting-and-formatting)
- [Submitting Pull Requests](#-submitting-pull-requests)

---

## 🤝 Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for everyone. When contributing to Nova VTU, please:
- Be respectful and constructive in discussions, issues, and code reviews.
- Focus on what is best for the community and project.
- Gracefully accept constructive feedback.

---

## 💡 How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing GitHub issues to make sure it hasn't already been reported.

When opening a new bug report, provide:
1. **Clear and descriptive title**: Summarize the issue briefly.
2. **Steps to reproduce**: Numbered steps to reproduce the behavior.
3. **Expected vs Actual behavior**: What you expected to happen vs what actually occurred.
4. **Environment details**: Python version, OS, browser (if UI issue), and relevant database.
5. **Logs / Tracebacks**: Any relevant terminal output, error traceback, or browser console logs (sanitize sensitive tokens/keys).

### Suggesting Enhancements

Feature requests and enhancement ideas are always welcome:
1. Open an issue describing the proposed feature or improvement.
2. Explain the use case and why this enhancement benefits Nova VTU users.
3. Discuss technical design considerations where applicable.

### Contributing Code

1. Pick an existing open issue or open one to discuss your planned change.
2. Fork the repository and create your feature/bugfix branch.
3. Implement your changes adhering to project standards and write corresponding tests.
4. Ensure all tests pass and linters are clean before submitting a PR.

### Improving Documentation

Documentation improvements (fixing typos, clarifying setup steps, adding API examples) are high-value contributions. You can edit Markdown files in `docs/` or `README.md` directly.

---

## 🛠️ Development Environment Setup

### Prerequisites

Ensure you have the following installed on your system:
- **Python 3.13+**
- **Git**
- **uv** (recommended for fast package management) or standard **pip** & **venv**
- **SQLite3** (default for local development) or **PostgreSQL 16+**

### Local Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dreww01/VTU.git
   cd VTU
   ```

2. **Set up the virtual environment & install dependencies:**

   *Using `uv` (recommended):*
   ```bash
   uv sync --all-extras --dev
   ```

   *Using standard `venv` & `pip`:*
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

### Environment Configuration

1. **Create your `.env` file:**
   ```bash
   cp .env.example .env
   ```

2. **Configure required environment variables:**
   - Generate a local `SECRET_KEY`:
     ```bash
     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
     ```
   - Set `DEBUG=True` for local development.
   - Configure sandbox API credentials for Paystack and VTPass if testing external integrations (or use mocked values for local tests).

### Database & Superuser Setup

1. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

2. **Create a superuser for accessing the Django Unfold admin panel:**
   ```bash
   python manage.py createsuperuser
   ```

3. **Start the development server:**
   ```bash
   python manage.py runserver
   ```
   Open `http://127.0.0.1:8000` in your browser to view the application, and `http://127.0.0.1:8000/admin` for the admin portal.

---

## 🏗️ Project Architecture & Structure

Nova VTU is structured as a modular Django application:

```
VTU/
├── accounts/          # User model, authentication, registration, profiles
├── wallet/            # Wallet ledger, balance operations, Paystack webhook & verification
├── transactions/      # Transaction records, statuses, history views, and receipts
├── config/            # Django settings (settings.py, urls.py, wsgi.py, asgi.py)
├── templates/         # HTML templates styled with Tailwind CSS
├── docs/              # Deployment guides and documentation
├── scripts/           # Maintenance and database backup utilities
├── manage.py          # Django management script
└── pyproject.toml     # Project configuration, dependencies, and tool settings
```

---

## 🔄 Development Workflow

### Branch Naming

Create branch names that clearly reflect the scope of work:
- `feature/<short-description>` (e.g. `feature/kyc-verification`)
- `fix/<short-description>` (e.g. `fix/webhook-replay-dedup`)
- `docs/<short-description>` (e.g. `docs/update-api-guide`)
- `refactor/<short-description>` (e.g. `refactor/transaction-service`)

### Commit Message Guidelines

We recommend following the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat: <description>` - A new feature
- `fix: <description>` - A bug fix
- `docs: <description>` - Documentation only changes
- `style: <description>` - Code style/formatting changes with no logic alteration
- `refactor: <description>` - Code changes that neither fix a bug nor add a feature
- `test: <description>` - Adding missing tests or correcting existing tests
- `chore: <description>` - Build process, tooling, or dependency updates

---

## 📐 Coding Standards & Best Practices

### Python & Django Guidelines

- **PEP 8:** Follow standard PEP 8 naming and formatting conventions.
- **Type Annotations:** Use Python type hints on public methods and functions.
- **Defensive Error Handling:** Handle expected edge cases and never catch base `Exception` without re-raising or logging actionable context.
- **Django Conventions:** Use Django's built-in ORM features, model methods, and decorators appropriately (e.g. `@login_required`, `@ratelimit`).

### Financial & Concurrency Safety

Handling user balances and digital top-ups demands strict financial correctness:
- **Use `Decimal` for Currency:** Never perform calculations on monetary values using `float`. Use Python's `Decimal` type.
- **Atomic Database Transactions:** Wrap multi-step balance changes in `transaction.atomic()`.
- **Concurrency Locking:** Use `select_for_update()` when modifying wallet balances to prevent race conditions during concurrent requests.
- **Idempotency:** Webhook endpoints and payment verification views must enforce idempotency using transaction reference checks.

### Security Best Practices

- **Never Commit Secrets:** Do not hardcode API keys, secret keys, or private tokens in code or commit `.env` files.
- **Timing-Safe Checks:** Use `hmac.compare_digest` when verifying webhook signatures to defend against timing attacks.
- **Rate Limiting:** Protect public and payment-related endpoints with appropriate rate limiting.

---

## 🧪 Testing & Quality Assurance

### Running Tests

Run the full automated test suite locally:

```bash
SECRET_KEY=test-secret-key python manage.py test
```

Or target specific apps:
```bash
SECRET_KEY=test-secret-key python manage.py test wallet
SECRET_KEY=test-secret-key python manage.py test accounts
SECRET_KEY=test-secret-key python manage.py test transactions
```

### Writing Tests

- All new features and bug fixes must be accompanied by comprehensive tests in the appropriate app (`accounts/tests.py`, `wallet/tests.py`, `transactions/tests.py`, etc.).
- External services (Paystack API, VTPass API, Resend Email) must be mocked in tests to keep the test suite hermetic, fast, and offline-capable.
- Test both happy paths and error/edge cases (e.g., insufficient funds, invalid signatures, malformed payloads, replay attacks).

### Linting and Formatting

Run linting checks before committing:

```bash
# Check code with Ruff
uv run ruff check .

# Check code formatting
uv run ruff format --check .
```

---

## 🚀 Submitting Pull Requests

1. **Keep PRs Focused:** Aim for single-purpose, reviewable pull requests.
2. **Update Documentation:** If your change modifies user-facing behavior or environment variables, update `README.md` or `.env.example`.
3. **Verify Tests:** Ensure all existing and new tests pass with 100% success.
4. **Open Pull Request:**
   - Give the PR a clear title and description.
   - Reference related issues (e.g., `Closes #12` or `Resolves #45`).
   - Describe what changed and how you verified it.
5. **Code Review:** Address any feedback promptly and constructively. Once approved, your PR will be merged into `main`.

Thank you for helping make Nova VTU better for everyone! 🇳🇬
