# GCP Deployment Quick Start

**Target**: Deploy Nova VTU to Google Cloud Run in ~30 minutes

## Prerequisites Checklist

- [ ] GCP account created
- [ ] `gcloud` CLI installed and configured
- [ ] Docker installed (for local testing)
- [ ] Domain name ready (optional but recommended)
- [ ] Paystack production keys
- [ ] VTPass production API credentials
- [ ] Resend API key for emails

---

## Step-by-Step Commands

### 1. Initial Setup (5 min)

```bash
# Set your project ID
export PROJECT_ID="nova-vtu-prod"  # Change this
export REGION="us-central1"
export SERVICE_NAME="nova-vtu"
export DB_INSTANCE_NAME="nova-vtu-db"

# Create project
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# Enable billing (required - do this in console)
# https://console.cloud.google.com/billing

# Enable APIs
gcloud services enable run.googleapis.com sqladmin.googleapis.com \
  storage.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

### 2. Database Setup (10 min)

```bash
# Create Cloud SQL instance (takes ~5-7 min)
gcloud sql instances create $DB_INSTANCE_NAME \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --root-password="CHANGE_THIS_PASSWORD"

# Create database
gcloud sql databases create novavtu --instance=$DB_INSTANCE_NAME

# Create user
gcloud sql users create django \
  --instance=$DB_INSTANCE_NAME \
  --password="CHANGE_THIS_PASSWORD"

# Get connection name (save this!)
gcloud sql instances describe $DB_INSTANCE_NAME --format='get(connectionName)'
```

### 3. Storage Setup (2 min)

```bash
# Create media bucket
gsutil mb -l $REGION gs://${PROJECT_ID}-media

# Make public
gsutil iam ch allUsers:objectViewer gs://${PROJECT_ID}-media
```

### 4. Secrets Setup (5 min)

```bash
# Django secret
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' | \
  gcloud secrets create django-secret-key --data-file=-

# Database URL (replace with your connection name and password)
echo "postgresql://django:YOUR_PASSWORD@//cloudsql/PROJECT:REGION:INSTANCE/novavtu" | \
  gcloud secrets create database-url --data-file=-

# Paystack
echo "sk_live_YOUR_KEY" | gcloud secrets create paystack-secret-key --data-file=-
echo "pk_live_YOUR_KEY" | gcloud secrets create paystack-public-key --data-file=-

# VTPass
echo "YOUR_API_KEY" | gcloud secrets create vtpass-api-key --data-file=-
echo "YOUR_SECRET" | gcloud secrets create vtpass-secret-key --data-file=-
echo "YOUR_PUBLIC_KEY" | gcloud secrets create vtpass-public-key --data-file=-

# Email
echo "re_YOUR_KEY" | gcloud secrets create resend-api-key --data-file=-

# Grant access
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in django-secret-key database-url paystack-secret-key paystack-public-key \
              vtpass-api-key vtpass-secret-key vtpass-public-key resend-api-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SA" \
    --role="roles/secretmanager.secretAccessor"
done
```

### 5. Build & Deploy (5 min)

```bash
# Build (takes 3-5 min)
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="DEBUG=False,ALLOWED_HOSTS=*,GCS_BUCKET_NAME=${PROJECT_ID}-media,VTPASS_BASE_URL=https://api.vtpass.com/api" \
  --set-secrets="SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest,PAYSTACK_SECRET_KEY=paystack-secret-key:latest,PAYSTACK_PUBLIC_KEY=paystack-public-key:latest,VTPASS_API_KEY=vtpass-api-key:latest,VTPASS_SECRET_KEY=vtpass-secret-key:latest,VTPASS_PUBLIC_KEY=vtpass-public-key:latest,RESEND_API_KEY=resend-api-key:latest" \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:$DB_INSTANCE_NAME \
  --memory=512Mi \
  --port=8080

# Get URL
gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)'
```

### 6. Post-Deployment (3 min)

```bash
# Run migrations
gcloud run jobs create migrate-db \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --region $REGION \
  --set-secrets="SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest" \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:$DB_INSTANCE_NAME \
  --command="python,manage.py,migrate"

gcloud run jobs execute migrate-db --region $REGION

# Update ALLOWED_HOSTS
export SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)' | sed 's|https://||')

gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --update-env-vars="ALLOWED_HOSTS=$SERVICE_URL,CSRF_TRUSTED_ORIGINS=https://$SERVICE_URL"
```

---

## Post-Launch Tasks

### Create Superuser

**Option 1: Cloud Shell Proxy**

```bash
# Download Cloud SQL Proxy
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
chmod +x cloud_sql_proxy

# Get connection name
export CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format='get(connectionName)')

# Start proxy
./cloud_sql_proxy -instances=$CONNECTION_NAME=tcp:5432 &

# Run command
DATABASE_URL="postgresql://django:YOUR_PASSWORD@127.0.0.1:5432/novavtu" \
SECRET_KEY="your-key" \
python manage.py createsuperuser
```

### Update Paystack Webhook

1. Go to https://dashboard.paystack.com/#/settings/webhooks
2. Set URL to: `https://YOUR_CLOUD_RUN_URL/wallet/webhook/`

### Test Everything

```bash
# Visit your site
curl https://YOUR_CLOUD_RUN_URL

# Check health
curl https://YOUR_CLOUD_RUN_URL/health/

# View logs
gcloud run services logs tail $SERVICE_NAME --region $REGION
```

---

## Common First-Time Issues

### 1. "Database connection refused"
**Solution**: Verify Cloud SQL instance is running and connection name is correct.

```bash
gcloud sql instances describe $DB_INSTANCE_NAME
```

### 2. "502 Bad Gateway"
**Solution**: Check logs for Python errors.

```bash
gcloud run services logs read $SERVICE_NAME --region $REGION --limit=50
```

### 3. "Static files not loading"
**Solution**: Check collectstatic ran during build.

```bash
# Rebuild
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME
```

### 4. "CSRF verification failed"
**Solution**: Update CSRF_TRUSTED_ORIGINS.

```bash
gcloud run services update $SERVICE_NAME \
  --update-env-vars="CSRF_TRUSTED_ORIGINS=https://YOUR_URL"
```

---

## Next Steps

1. **Custom Domain**: See [gcp-deployment.md](gcp-deployment.md#custom-domain--ssl)
2. **Monitoring**: Set up alerts in Cloud Console
3. **Backups**: Verify Cloud SQL backups are enabled
4. **SSL**: Automatic with custom domain
5. **CI/CD**: Set up GitHub Actions (optional)

---

## Quick Reference Commands

```bash
# View logs
gcloud run services logs tail $SERVICE_NAME --region $REGION

# Update service
gcloud run services update $SERVICE_NAME --region $REGION --image gcr.io/$PROJECT_ID/$SERVICE_NAME

# Redeploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME && \
gcloud run services update $SERVICE_NAME --region $REGION --image gcr.io/$PROJECT_ID/$SERVICE_NAME

# Check status
gcloud run services describe $SERVICE_NAME --region $REGION

# View secrets
gcloud secrets list

# Database backup
gcloud sql backups create --instance=$DB_INSTANCE_NAME
```

---

## Rollback Plan

If something goes wrong:

```bash
# List revisions
gcloud run revisions list --service=$SERVICE_NAME --region=$REGION

# Rollback to previous revision
gcloud run services update-traffic $SERVICE_NAME \
  --to-revisions=REVISION_NAME=100 \
  --region=$REGION
```

---

## Cost Estimate

**Minimal setup**: ~$15-25/month
- Cloud Run: $5-10 (mostly idle)
- Cloud SQL (db-f1-micro): $7-10
- Storage: $1-5

**Budget alert** (recommended):

```bash
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Nova VTU Alert" \
  --budget-amount=30USD \
  --threshold-rule=percent=80
```

---

## Emergency Contacts

- **GCP Support**: https://cloud.google.com/support
- **Django Docs**: https://docs.djangoproject.com
- **Cloud Run Docs**: https://cloud.google.com/run/docs

---

## Success Checklist

- [ ] Application accessible via Cloud Run URL
- [ ] Database connected (check admin panel)
- [ ] Static files loading
- [ ] User registration works
- [ ] Login/logout works
- [ ] Paystack funding works (test mode first)
- [ ] VTPass transactions work (test mode)
- [ ] Emails sending
- [ ] Admin panel accessible
- [ ] Logs visible in Cloud Console
- [ ] No errors in logs
- [ ] Custom domain configured (if applicable)
- [ ] SSL certificate active
- [ ] Backups enabled

**You're live! 🚀**
