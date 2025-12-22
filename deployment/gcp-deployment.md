# Nova VTU - Google Cloud Platform Deployment Guide

This guide walks you through deploying Nova VTU to Google Cloud Platform using Cloud Run, Cloud SQL, and Cloud Storage.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GCP Setup](#gcp-setup)
3. [Database Setup (Cloud SQL)](#database-setup)
4. [Storage Setup (Cloud Storage)](#storage-setup)
5. [Secrets Management](#secrets-management)
6. [Deploy to Cloud Run](#deploy-to-cloud-run)
7. [Post-Deployment Tasks](#post-deployment-tasks)
8. [Custom Domain & SSL](#custom-domain--ssl)
9. [Monitoring & Logging](#monitoring--logging)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Local Requirements

- Python 3.13+
- Docker installed and running
- Google Cloud SDK (`gcloud` CLI)
- Git

### Install Google Cloud SDK

**macOS/Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Windows:**
Download from: https://cloud.google.com/sdk/docs/install

**Verify Installation:**
```bash
gcloud --version
```

---

## GCP Setup

### 1. Create GCP Account & Project

1. Go to https://console.cloud.google.com
2. Create a new project (e.g., "nova-vtu-prod")
3. Note your `PROJECT_ID`

### 2. Enable Required APIs

```bash
# Set your project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  vpcaccess.googleapis.com
```

### 3. Set Environment Variables

```bash
export REGION="us-central1"  # Choose your region
export SERVICE_NAME="nova-vtu"
export DB_INSTANCE_NAME="nova-vtu-db"
```

---

## Database Setup

### 1. Create Cloud SQL PostgreSQL Instance

```bash
gcloud sql instances create $DB_INSTANCE_NAME \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --root-password="CHANGE_ME_STRONG_PASSWORD" \
  --storage-type=SSD \
  --storage-size=10GB \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04
```

**⚠️ Production Recommendation:**
- Use `db-g1-small` or higher for production
- Enable automatic backups (enabled by default)
- Set retention period: `--backup-retention=7`

### 2. Create Database

```bash
gcloud sql databases create novavtu \
  --instance=$DB_INSTANCE_NAME
```

### 3. Create Database User

```bash
gcloud sql users create django \
  --instance=$DB_INSTANCE_NAME \
  --password="CHANGE_ME_DB_USER_PASSWORD"
```

### 4. Get Connection Name

```bash
gcloud sql instances describe $DB_INSTANCE_NAME \
  --format='get(connectionName)'
```

**Save this for later!** Format: `PROJECT_ID:REGION:DB_INSTANCE_NAME`

---

## Storage Setup

### 1. Create Storage Buckets

```bash
# Bucket for media files (avatars)
gsutil mb -l $REGION gs://${PROJECT_ID}-media

# Bucket for static files (optional, can use WhiteNoise)
gsutil mb -l $REGION gs://${PROJECT_ID}-static
```

### 2. Set Bucket Permissions

```bash
# Make media files publicly readable (for avatars)
gsutil iam ch allUsers:objectViewer gs://${PROJECT_ID}-media

# Keep static files public too
gsutil iam ch allUsers:objectViewer gs://${PROJECT_ID}-static
```

### 3. Enable CORS (if needed for frontend)

Create `cors.json`:
```json
[
  {
    "origin": ["https://yourdomain.com"],
    "method": ["GET", "HEAD"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
```

Apply:
```bash
gsutil cors set cors.json gs://${PROJECT_ID}-media
```

---

## Secrets Management

### 1. Create Secrets in Secret Manager

```bash
# Django secret key
echo -n "$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" | \
  gcloud secrets create django-secret-key --data-file=-

# Database URL
echo -n "postgresql://django:YOUR_DB_PASSWORD@//cloudsql/$PROJECT_ID:$REGION:$DB_INSTANCE_NAME/novavtu" | \
  gcloud secrets create database-url --data-file=-

# Paystack Secret Key
echo -n "sk_live_YOUR_PAYSTACK_SECRET_KEY" | \
  gcloud secrets create paystack-secret-key --data-file=-

# Paystack Public Key
echo -n "pk_live_YOUR_PAYSTACK_PUBLIC_KEY" | \
  gcloud secrets create paystack-public-key --data-file=-

# VTPass API Key
echo -n "YOUR_VTPASS_API_KEY" | \
  gcloud secrets create vtpass-api-key --data-file=-

# VTPass Secret Key
echo -n "YOUR_VTPASS_SECRET_KEY" | \
  gcloud secrets create vtpass-secret-key --data-file=-

# VTPass Public Key
echo -n "YOUR_VTPASS_PUBLIC_KEY" | \
  gcloud secrets create vtpass-public-key --data-file=-

# Resend API Key
echo -n "re_YOUR_RESEND_API_KEY" | \
  gcloud secrets create resend-api-key --data-file=-
```

### 2. Grant Cloud Run Access to Secrets

```bash
# Get Cloud Run service account
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant access to all secrets
for secret in django-secret-key database-url paystack-secret-key paystack-public-key \
              vtpass-api-key vtpass-secret-key vtpass-public-key resend-api-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## Deploy to Cloud Run

### 1. Build and Push Container Image

**Option A: Using Cloud Build (Recommended)**

```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME
```

**Option B: Using Docker locally**

```bash
# Build locally
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME .

# Authenticate Docker
gcloud auth configure-docker

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME
```

### 2. Deploy to Cloud Run

```bash
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="DEBUG=False,ALLOWED_HOSTS=*,GCS_BUCKET_NAME=${PROJECT_ID}-media" \
  --set-secrets="SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest,PAYSTACK_SECRET_KEY=paystack-secret-key:latest,PAYSTACK_PUBLIC_KEY=paystack-public-key:latest,VTPASS_API_KEY=vtpass-api-key:latest,VTPASS_SECRET_KEY=vtpass-secret-key:latest,VTPASS_PUBLIC_KEY=vtpass-public-key:latest,RESEND_API_KEY=resend-api-key:latest" \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:$DB_INSTANCE_NAME \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=300 \
  --port=8080
```

### 3. Get Service URL

```bash
gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)'
```

**Save this URL!** This is your application URL.

---

## Post-Deployment Tasks

### 1. Run Database Migrations

```bash
# Connect to Cloud SQL and run migrations via Cloud Run job
gcloud run jobs create migrate-db \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --region $REGION \
  --set-secrets="SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest" \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:$DB_INSTANCE_NAME \
  --command="python,manage.py,migrate"

# Execute the migration job
gcloud run jobs execute migrate-db --region $REGION
```

**Or manually via Cloud Shell:**

```bash
# Install Cloud SQL Proxy
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
chmod +x cloud_sql_proxy

# Start proxy in background
./cloud_sql_proxy -instances=$PROJECT_ID:$REGION:$DB_INSTANCE_NAME=tcp:5432 &

# Run migrations (in your local project directory)
DATABASE_URL="postgresql://django:YOUR_PASSWORD@127.0.0.1:5432/novavtu" \
SECRET_KEY="your-secret-key" \
python manage.py migrate
```

### 2. Create Superuser

```bash
# Create admin job
gcloud run jobs create create-superuser \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --region $REGION \
  --set-secrets="SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest" \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:$DB_INSTANCE_NAME \
  --command="python,manage.py,createsuperuser,--noinput,--username=admin,--email=admin@yourdomain.com"

# Or do it interactively via Cloud Shell with proxy running
python manage.py createsuperuser
```

### 3. Update ALLOWED_HOSTS

Update your Cloud Run service with the correct domain:

```bash
# Get your Cloud Run URL
export SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)' | sed 's|https://||')

gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --update-env-vars="ALLOWED_HOSTS=$SERVICE_URL,yourdomain.com,www.yourdomain.com"
```

### 4. Update Paystack Webhook URL

1. Go to Paystack Dashboard → Settings → Webhooks
2. Update webhook URL to: `https://YOUR_CLOUD_RUN_URL/wallet/webhook/`

### 5. Configure CSRF Trusted Origins

```bash
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --update-env-vars="CSRF_TRUSTED_ORIGINS=https://$SERVICE_URL,https://yourdomain.com"
```

---

## Custom Domain & SSL

### 1. Map Custom Domain

```bash
gcloud run domain-mappings create \
  --service=$SERVICE_NAME \
  --domain=yourdomain.com \
  --region=$REGION
```

### 2. Configure DNS

Cloud Run will provide DNS records. Add them to your domain registrar:

```bash
# View DNS records
gcloud run domain-mappings describe --domain=yourdomain.com --region=$REGION
```

Add the provided A and AAAA records to your DNS.

### 3. SSL Certificate

Cloud Run automatically provisions SSL certificates for custom domains (usually within 15 minutes).

**Verify SSL:**
```bash
curl -I https://yourdomain.com
```

---

## Monitoring & Logging

### 1. View Logs

```bash
# Real-time logs
gcloud run services logs tail $SERVICE_NAME --region $REGION

# Recent logs
gcloud run services logs read $SERVICE_NAME --region $REGION --limit=50
```

### 2. View in Cloud Console

https://console.cloud.google.com/logs

Filter: `resource.labels.service_name="nova-vtu"`

### 3. Set Up Alerts

```bash
# Create alert for errors
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="Nova VTU Error Alert" \
  --condition-display-name="Error Rate" \
  --condition-threshold-value=10 \
  --condition-threshold-duration=60s
```

### 4. Enable Cloud Monitoring

```bash
# Install monitoring agent in your application (optional)
pip install google-cloud-monitoring
```

---

## Environment Configuration

### Update Django Settings for GCP

Your `config/settings.py` should already handle this via environment variables. Ensure these are set:

**Required Environment Variables:**
```bash
DEBUG=False
SECRET_KEY=<from Secret Manager>
DATABASE_URL=<from Secret Manager>
ALLOWED_HOSTS=<your-domain.com>
CSRF_TRUSTED_ORIGINS=https://<your-domain.com>

# VTPass
VTPASS_BASE_URL=https://api.vtpass.com/api  # Production URL
VTPASS_API_KEY=<from Secret Manager>
VTPASS_SECRET_KEY=<from Secret Manager>
VTPASS_PUBLIC_KEY=<from Secret Manager>

# Paystack
PAYSTACK_SECRET_KEY=<from Secret Manager>
PAYSTACK_PUBLIC_KEY=<from Secret Manager>

# Email
RESEND_API_KEY=<from Secret Manager>
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# GCS Storage
GCS_BUCKET_NAME=${PROJECT_ID}-media
GCS_STATIC_BUCKET_NAME=${PROJECT_ID}-static  # Optional
```

### Optional: Configure Cloud Storage in Django

If you want to use GCS for media files, update `config/settings.py`:

```python
# Add to settings.py for production
if not DEBUG:
    # Google Cloud Storage
    DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
    GS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
    GS_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/'
```

---

## Continuous Deployment

### Set Up GitHub Actions (Optional)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main

env:
  PROJECT_ID: your-project-id
  SERVICE_NAME: nova-vtu
  REGION: us-central1

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - id: auth
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1

      - name: Build and Push Container
        run: |
          gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE_NAME \
            --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
            --region $REGION \
            --platform managed
```

---

## Troubleshooting

### Common Issues

**1. Container fails to start**
```bash
# Check logs
gcloud run services logs read $SERVICE_NAME --region $REGION --limit=100

# Common causes:
# - Missing environment variables
# - Database connection failure
# - Port mismatch (ensure PORT=8080)
```

**2. Database connection refused**
```bash
# Verify Cloud SQL instance is running
gcloud sql instances describe $DB_INSTANCE_NAME

# Check Cloud Run has Cloud SQL connection
gcloud run services describe $SERVICE_NAME --region $REGION
```

**3. Static files not loading**
```bash
# Rebuild and collectstatic
docker build -t test .
docker run -e SECRET_KEY=test test python manage.py collectstatic --noinput
```

**4. 502 Bad Gateway**
```bash
# Usually means app crashed on startup
# Check logs for Python errors
gcloud run services logs tail $SERVICE_NAME --region $REGION
```

**5. Database migrations needed**
```bash
# Run migrations via Cloud Run job (see Post-Deployment Tasks)
# Or use Cloud SQL Proxy locally
```

### Health Check Endpoint

Add a health check to your Django app:

```python
# In config/urls.py
from django.http import JsonResponse

def health(request):
    return JsonResponse({'status': 'healthy'})

urlpatterns = [
    path('health/', health),
    # ... other patterns
]
```

---

## Cost Optimization

### Estimated Monthly Costs (Low Traffic)

- **Cloud Run**: ~$5-15/month (based on usage)
- **Cloud SQL (db-f1-micro)**: ~$7-10/month
- **Cloud Storage**: ~$1-5/month
- **Total**: ~$15-30/month

### Cost-Saving Tips

1. **Use minimum instances = 0** (cold starts OK for low traffic)
2. **Enable request-based autoscaling**
3. **Use Cloud SQL instance scheduling** (stop during off-hours if acceptable)
4. **Monitor with Cloud Monitoring free tier**
5. **Use Cloud CDN** for static assets (optional)

### Set Budget Alerts

```bash
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="Nova VTU Budget" \
  --budget-amount=50USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

---

## Production Checklist

Before going live:

- [ ] Change `DEBUG=False`
- [ ] Set strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` correctly
- [ ] Set `CSRF_TRUSTED_ORIGINS`
- [ ] Enable HTTPS redirect
- [ ] Configure proper database backups
- [ ] Set up monitoring alerts
- [ ] Test Paystack webhook
- [ ] Test VTPass transactions (use production API)
- [ ] Configure custom domain & SSL
- [ ] Set up email (Resend production)
- [ ] Review transaction limits
- [ ] Test authentication flow
- [ ] Verify media uploads work
- [ ] Run security audit
- [ ] Load test application
- [ ] Document incident response plan

---

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Django on Cloud Run](https://cloud.google.com/python/django/run)
- [Google Cloud Free Tier](https://cloud.google.com/free)

---

## Support

For issues specific to this deployment:
1. Check application logs in Cloud Logging
2. Review Cloud Run service configuration
3. Verify all secrets are correctly set
4. Test database connectivity

For GCP platform issues:
- https://cloud.google.com/support
