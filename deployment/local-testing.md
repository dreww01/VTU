# Testing Your Docker Setup Locally

Before deploying to GCP, test your containerized app locally to catch issues early.

## Quick Local Test

### 1. Build the Docker Image

```bash
docker build -t nova-vtu:test .
```

**Expected output**: Build should complete without errors and show "Collecting static files..."

### 2. Test with SQLite (Quick Test)

```bash
docker run -p 8080:8080 \
  -e SECRET_KEY="test-secret-key-12345" \
  -e DEBUG="True" \
  -e ALLOWED_HOSTS="localhost,127.0.0.1" \
  nova-vtu:test
```

**Visit**: http://localhost:8080

### 3. Test with PostgreSQL (Production-like)

#### Start PostgreSQL Container

```bash
docker run -d \
  --name postgres-test \
  -e POSTGRES_DB=novavtu \
  -e POSTGRES_USER=django \
  -e POSTGRES_PASSWORD=testpass123 \
  -p 5432:5432 \
  postgres:15
```

#### Run Migrations

```bash
docker run --rm \
  --network host \
  -e SECRET_KEY="test-secret-key-12345" \
  -e DATABASE_URL="postgresql://django:testpass123@localhost:5432/novavtu" \
  nova-vtu:test \
  python manage.py migrate
```

#### Start Application

```bash
docker run -p 8080:8080 \
  --network host \
  -e SECRET_KEY="test-secret-key-12345" \
  -e DEBUG="False" \
  -e DATABASE_URL="postgresql://django:testpass123@localhost:5432/novavtu" \
  -e ALLOWED_HOSTS="localhost,127.0.0.1" \
  -e CSRF_TRUSTED_ORIGINS="http://localhost:8080" \
  nova-vtu:test
```

#### Create Superuser

```bash
docker run --rm -it \
  --network host \
  -e SECRET_KEY="test-secret-key-12345" \
  -e DATABASE_URL="postgresql://django:testpass123@localhost:5432/novavtu" \
  nova-vtu:test \
  python manage.py createsuperuser
```

---

## Using Docker Compose (Recommended)

Create `docker-compose.test.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: novavtu
      POSTGRES_USER: django
      POSTGRES_PASSWORD: testpass123
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8080 --reload
    environment:
      - SECRET_KEY=test-secret-key-for-local-development
      - DEBUG=True
      - DATABASE_URL=postgresql://django:testpass123@db:5432/novavtu
      - ALLOWED_HOSTS=localhost,127.0.0.1
      - CSRF_TRUSTED_ORIGINS=http://localhost:8080
      # Add your test API keys here
      - VTPASS_BASE_URL=https://sandbox.vtpass.com/api
      - VTPASS_API_KEY=your_test_key
      - VTPASS_SECRET_KEY=your_test_secret
      - PAYSTACK_SECRET_KEY=sk_test_your_key
      - PAYSTACK_PUBLIC_KEY=pk_test_your_key
      - RESEND_API_KEY=re_test_your_key
    ports:
      - "8080:8080"
    depends_on:
      - db
    volumes:
      - ./media:/app/media

volumes:
  postgres_data:
```

### Commands

```bash
# Start everything
docker-compose -f docker-compose.test.yml up

# Run migrations
docker-compose -f docker-compose.test.yml run web python manage.py migrate

# Create superuser
docker-compose -f docker-compose.test.yml run web python manage.py createsuperuser

# View logs
docker-compose -f docker-compose.test.yml logs -f

# Stop
docker-compose -f docker-compose.test.yml down

# Clean up (remove volumes)
docker-compose -f docker-compose.test.yml down -v
```

---

## Testing Checklist

### Build Phase
- [ ] Image builds successfully
- [ ] No missing dependencies
- [ ] Static files collected
- [ ] Image size reasonable (<500MB)

### Runtime Phase
- [ ] Container starts without errors
- [ ] Health check passes
- [ ] Database connection works
- [ ] Static files serve correctly
- [ ] Admin panel accessible
- [ ] Login/logout works
- [ ] Registration works

### API Tests
- [ ] Paystack test webhook works
- [ ] VTPass sandbox API works
- [ ] Email sending works (check logs)

---

## Common Local Issues

### Issue: "Cannot find module X"
**Solution**: Rebuild image after adding to pyproject.toml

```bash
docker build --no-cache -t nova-vtu:test .
```

### Issue: "Static files 404"
**Solution**: Check collectstatic ran

```bash
docker run --rm nova-vtu:test ls -la /app/staticfiles
```

### Issue: "Database connection refused"
**Solution**: Use `host.docker.internal` on Mac/Windows

```bash
# Instead of localhost, use:
-e DATABASE_URL="postgresql://django:testpass123@host.docker.internal:5432/novavtu"
```

### Issue: "Port already in use"
**Solution**: Change port mapping

```bash
docker run -p 8000:8080 ...  # Access on localhost:8000
```

---

## Performance Testing

### Check Memory Usage

```bash
docker stats
```

**Expected**: <200MB memory usage under normal load

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils  # Linux
brew install httpd  # macOS

# Test
ab -n 1000 -c 10 http://localhost:8080/
```

### Check Startup Time

```bash
time docker run --rm nova-vtu:test python -c "import django; django.setup()"
```

**Expected**: <5 seconds

---

## Debugging Tips

### Access Container Shell

```bash
docker run --rm -it \
  -e SECRET_KEY="test-key" \
  nova-vtu:test \
  /bin/bash
```

### Check Environment Variables

```bash
docker run --rm nova-vtu:test env
```

### View Django Check

```bash
docker run --rm \
  -e SECRET_KEY="test-key" \
  -e DATABASE_URL="sqlite:///db.sqlite3" \
  nova-vtu:test \
  python manage.py check --deploy
```

### Test Database Connection

```bash
docker run --rm \
  -e SECRET_KEY="test-key" \
  -e DATABASE_URL="postgresql://django:testpass123@host.docker.internal:5432/novavtu" \
  nova-vtu:test \
  python manage.py dbshell
```

---

## Pre-Deployment Checklist

Before pushing to GCP:

- [ ] **Build succeeds**: No errors during `docker build`
- [ ] **App starts**: Container runs without crashes
- [ ] **Database connects**: With PostgreSQL container
- [ ] **Migrations work**: No migration errors
- [ ] **Static files load**: CSS/JS accessible
- [ ] **Admin works**: Can login to `/admin/`
- [ ] **Registration works**: New user creation
- [ ] **Authentication works**: Login/logout
- [ ] **Environment vars work**: Configured via `-e` flags
- [ ] **Port 8080**: App responds on correct port
- [ ] **No secrets in image**: No .env file in container
- [ ] **Health check passes**: If implemented
- [ ] **Gunicorn runs**: Production server works
- [ ] **No DEBUG warnings**: Django check --deploy passes

---

## CI/CD Testing

### GitHub Actions Test Workflow

Create `.github/workflows/test.yml`:

```yaml
name: Test Docker Build

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: novavtu
          POSTGRES_USER: django
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -t test-image .

      - name: Run migrations
        run: |
          docker run --network host \
            -e SECRET_KEY=test \
            -e DATABASE_URL=postgresql://django:testpass@localhost:5432/novavtu \
            test-image python manage.py migrate

      - name: Run tests
        run: |
          docker run --network host \
            -e SECRET_KEY=test \
            -e DATABASE_URL=postgresql://django:testpass@localhost:5432/novavtu \
            test-image python manage.py test
```

---

## Next Steps

Once local testing passes:
1. Review [gcp-deployment.md](gcp-deployment.md) for full deployment guide
2. Or use [quick-start.md](quick-start.md) for fast deployment
3. Ensure all API keys are production-ready
4. Double-check environment variables

**Ready to deploy? Let's go! 🚀**
