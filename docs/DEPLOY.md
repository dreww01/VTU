# Nova VTU - GCP Deployment

Quick guide to deploy Nova VTU on Google Cloud Run with Neon PostgreSQL.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed
- Neon PostgreSQL database (already set up)

## 1. Initial Setup (One-time)

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Login and set project
gcloud auth login
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com
```

## 2. Create Secrets

```bash
# Django secret key
python -c "from secrets import token_urlsafe; print(token_urlsafe(50))" | \
  gcloud secrets create django-secret-key --data-file=-

# Neon database URL (get from Neon dashboard)
echo -n "postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require" | \
  gcloud secrets create database-url --data-file=-

# API keys (replace with your actual keys)
echo -n "sk_live_xxx" | gcloud secrets create paystack-secret-key --data-file=-
echo -n "pk_live_xxx" | gcloud secrets create paystack-public-key --data-file=-
echo -n "xxx" | gcloud secrets create vtpass-api-key --data-file=-
echo -n "xxx" | gcloud secrets create vtpass-secret-key --data-file=-
echo -n "re_xxx" | gcloud secrets create resend-api-key --data-file=-
```

## 3. Grant Secret Access

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in django-secret-key database-url paystack-secret-key paystack-public-key vtpass-api-key vtpass-secret-key resend-api-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SA" \
    --role="roles/secretmanager.secretAccessor"
done
```

## 4. Deploy

```bash
# Build and push image
gcloud builds submit --tag gcr.io/$PROJECT_ID/nova-vtu

# Deploy to Cloud Run
gcloud run deploy nova-vtu \
  --image gcr.io/$PROJECT_ID/nova-vtu \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --set-env-vars "DEBUG=False" \
  --set-secrets "SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest,PAYSTACK_SECRET_KEY=paystack-secret-key:latest,PAYSTACK_PUBLIC_KEY=paystack-public-key:latest,VTPASS_API_KEY=vtpass-api-key:latest,VTPASS_SECRET_KEY=vtpass-secret-key:latest,RESEND_API_KEY=resend-api-key:latest"
```

## 5. Run Migrations

```bash
# Create migration job
gcloud run jobs create migrate \
  --image gcr.io/$PROJECT_ID/nova-vtu \
  --region $REGION \
  --set-secrets "SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest" \
  --command "python,manage.py,migrate"

# Execute
gcloud run jobs execute migrate --region $REGION

# Get your URL
gcloud run services describe nova-vtu --region $REGION --format 'value(status.url)'
```

## GitHub Actions Setup

Add these secrets to your GitHub repo (Settings > Secrets > Actions):

| Secret | Value |
|--------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_WIF_PROVIDER` | Workload Identity Federation provider |
| `GCP_SA_EMAIL` | Service account email |

### Create Workload Identity Federation

```bash
# Create service account
gcloud iam service-accounts create github-actions --display-name="GitHub Actions"
SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant roles
for role in run.admin storage.admin iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/$role"
done

# Create workload identity pool
gcloud iam workload-identity-pools create github --location="global"

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location="global" \
  --workload-identity-pool="github" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Allow GitHub repo (replace OWNER/REPO)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/OWNER/REPO"

# Get values for GitHub secrets
echo "GCP_SA_EMAIL: $SA_EMAIL"
echo "GCP_WIF_PROVIDER: projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/providers/github-provider"
```

## Quick Commands

```bash
# View logs
gcloud run services logs tail nova-vtu --region $REGION

# Redeploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/nova-vtu && \
gcloud run deploy nova-vtu --image gcr.io/$PROJECT_ID/nova-vtu --region $REGION

# Set custom domain
gcloud run domain-mappings create --service nova-vtu --domain yourdomain.com --region $REGION
```

## Costs

- Cloud Run: ~$5-15/month (usage-based, free tier available)
- Neon: Free tier or ~$19/month for Pro
- **Total**: ~$5-35/month
