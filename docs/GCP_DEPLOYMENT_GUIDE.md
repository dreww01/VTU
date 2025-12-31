# Nova VTU - GCP Cloud Run Deployment Guide

Complete guide for deploying Nova VTU to Google Cloud Run with GitHub Actions CI/CD.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Method A: Terminal (gcloud CLI)](#method-a-terminal-gcloud-cli)
3. [Method B: GCP Console (Web UI)](#method-b-gcp-console-web-ui)
4. [GitHub Actions Setup](#github-actions-setup)
5. [Troubleshooting](#troubleshooting)
6. [Quick Reference](#quick-reference)

---

## Prerequisites

### Required Accounts
- Google Cloud Platform account with billing enabled
- GitHub repository with your code
- PostgreSQL database (Neon, Supabase, or Cloud SQL)

### Required Tools (for Terminal method)
```bash
# Install Google Cloud SDK
# Windows: https://cloud.google.com/sdk/docs/install
# Or via winget:
winget install Google.CloudSDK
```

### Project Values Reference
```
Project ID:       your-project-id
Project Number:   123456789012
Region:           us-central1
Service Name:     nova-vtu
```

---

## Method A: Terminal (gcloud CLI)

### Step 1: Authenticate & Set Project

```bash
# Login to GCP
gcloud auth login

# Set your project
gcloud config set project your-project-id

# Verify
gcloud config get-value project
```

### Step 2: Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com
```

### Step 3: Create Service Account for GitHub Actions

```bash
# Create service account
gcloud iam service-accounts create github-actions-vtu \
  --display-name="GitHub Actions Deployer"

# Store email for later use
SA_EMAIL="github-actions-deployer@your-project-id.iam.gserviceaccount.com"

# Grant required roles
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser"
```

### Step 4: Setup Workload Identity Federation (Keyless Auth)

```bash
# Create workload identity pool
gcloud iam workload-identity-pools create github-pool \
  --location="global" \
  --display-name="GitHub Pool"

# Create OIDC provider for GitHub
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Get the provider resource name (you'll need this for GitHub)
gcloud iam workload-identity-pools providers describe github-provider \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"
# Output: projects/123456789012/locations/global/workloadIdentityPools/github-pool/providers/github-provider

# Allow GitHub repo to impersonate service account
# Replace YOUR_GITHUB_USERNAME/YOUR_REPO with your actual repo
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/123456789012/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GITHUB_USERNAME/YOUR_REPO"
```

### Step 5: Create Secrets in Secret Manager

```bash
# Create each secret (use lowercase names to match workflow)
echo -n "your-django-secret-key-here" | \
  gcloud secrets create django-secret-key --data-file=-

echo -n "postgresql://user:pass@host:5432/dbname" | \
  gcloud secrets create database-url --data-file=-

echo -n "sk_live_xxxxx" | \
  gcloud secrets create paystack-secret-key --data-file=-

echo -n "pk_live_xxxxx" | \
  gcloud secrets create paystack-public-key --data-file=-

echo -n "your-vtpass-api-key" | \
  gcloud secrets create vtpass-api-key --data-file=-

echo -n "your-vtpass-secret-key" | \
  gcloud secrets create vtpass-secret-key --data-file=-

echo -n "re_xxxxx" | \
  gcloud secrets create resend-api-key --data-file=-

# Grant service account access to secrets
for secret in django-secret-key database-url paystack-secret-key paystack-public-key vtpass-api-key vtpass-secret-key resend-api-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor"
done
```

### Step 6: Deploy Manually (First Time / Testing)

```bash
# Build and deploy from local
gcloud run deploy nova-vtu \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets "SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest,PAYSTACK_SECRET_KEY=paystack-secret-key:latest,PAYSTACK_PUBLIC_KEY=paystack-public-key:latest,VTPASS_API_KEY=vtpass-api-key:latest,VTPASS_SECRET_KEY=vtpass-secret-key:latest,RESEND_API_KEY=resend-api-key:latest" \
  --set-env-vars "DEBUG=False,ALLOWED_HOSTS=.run.app"
```

### Step 7: Make Service Public

```bash
gcloud run services add-iam-policy-binding nova-vtu \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

---

## Method B: GCP Console (Web UI)

### Step 1: Create Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click project dropdown → **New Project**
3. Enter:
   - Project name: `nova-vtu-prod`
   - Organization: (your org or leave blank)
4. Click **Create**
5. Select the new project from dropdown

### Step 2: Enable APIs

1. Go to **APIs & Services** → **Library**
2. Search and enable each:
   - Cloud Run API
   - Secret Manager API
   - Artifact Registry API
   - Cloud Build API
   - IAM API
   - IAM Service Account Credentials API

### Step 3: Create Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **+ Create Service Account**
3. Enter:
   - Name: `github-actions-vtu`
   - Description: `GitHub Actions Deployer`
4. Click **Create and Continue**
5. Add roles (click **+ Add Another Role** for each):
   - `Cloud Run Admin`
   - `Storage Admin`
   - `Secret Manager Secret Accessor`
   - `Service Account User`
6. Click **Done**
7. Note the email: `github-actions-deployer@your-project-id.iam.gserviceaccount.com`

### Step 4: Setup Workload Identity Federation

1. Go to **IAM & Admin** → **Workload Identity Federation**
2. Click **Create Pool**
3. Enter:
   - Name: `github-pool`
   - Description: `GitHub Actions authentication`
4. Click **Continue**
5. Select **OpenID Connect (OIDC)**
6. Enter:
   - Provider name: `github-provider`
   - Issuer URL: `https://token.actions.githubusercontent.com`
7. Click **Continue**
8. Configure attribute mapping:
   - `google.subject` = `assertion.sub`
   - Click **Add Mapping**:
     - `attribute.repository` = `assertion.repository`
     - `attribute.repository_owner` = `assertion.repository_owner`
9. Click **Save**

**Connect Service Account:**

1. In the pool details, click **Grant Access**
2. Select your service account: `github-actions-deployer@...`
3. For attribute name, select `repository`
4. For attribute value, enter: `YOUR_GITHUB_USERNAME/YOUR_REPO`
5. Click **Save**
6. Copy the **Provider Resource Name** (format: `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL/providers/PROVIDER`)

### Step 5: Create Secrets

1. Go to **Security** → **Secret Manager**
2. Click **+ Create Secret** for each:

| Secret Name | Value |
|-------------|-------|
| `django-secret-key` | Your Django secret key |
| `database-url` | `postgresql://user:pass@host:5432/db` |
| `paystack-secret-key` | `sk_live_xxxxx` |
| `paystack-public-key` | `pk_live_xxxxx` |
| `vtpass-api-key` | Your VTPass API key |
| `vtpass-secret-key` | Your VTPass secret |
| `resend-api-key` | `re_xxxxx` |

**Grant Access to Each Secret:**

1. Click on secret name
2. Go to **Permissions** tab
3. Click **Grant Access**
4. Add principal: `github-actions-deployer@your-project-id.iam.gserviceaccount.com`
5. Role: `Secret Manager Secret Accessor`
6. Click **Save**

### Step 6: Deploy via Cloud Run UI

1. Go to **Cloud Run**
2. Click **Create Service**
3. Select **Continuously deploy from a repository**
4. Connect your GitHub repo
5. Configure:
   - Service name: `nova-vtu`
   - Region: `us-central1`
   - CPU allocation: CPU is only allocated during request processing
   - Minimum instances: 0
   - Maximum instances: 10
6. Under **Container** → **Variables & Secrets**:
   - Add environment variables:
     - `DEBUG` = `False`
     - `ALLOWED_HOSTS` = `.run.app`
   - Click **Reference a Secret**:
     - Variable: `SECRET_KEY`, Secret: `django-secret-key`, Version: `latest`
     - Repeat for all other secrets
7. Under **Security**:
   - Check **Allow unauthenticated invocations**
8. Click **Create**

---

## GitHub Actions Setup

### Step 1: Add Repository Secrets

Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `GCP_PROJECT_ID` | `your-project-id` |
| `GCP_SA_EMAIL` | `github-actions-deployer@your-project-id.iam.gserviceaccount.com` |
| `GCP_WIF_PROVIDER` | `projects/123456789012/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |

⚠️ **IMPORTANT**: Don't swap these values! `GCP_WIF_PROVIDER` should be the long path, `GCP_SA_EMAIL` should be the email.

### Step 2: Workflow File

Your `.github/workflows/deploy.yml` should look like:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [master]
  workflow_dispatch:

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: us-central1
  SERVICE: nova-vtu

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service_account: ${{ secrets.GCP_SA_EMAIL }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE \
            --source . \
            --region $REGION \
            --platform managed \
            --allow-unauthenticated \
            --clear-secrets \
            --set-secrets "SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest,PAYSTACK_SECRET_KEY=paystack-secret-key:latest,PAYSTACK_PUBLIC_KEY=paystack-public-key:latest,VTPASS_API_KEY=vtpass-api-key:latest,VTPASS_SECRET_KEY=vtpass-secret-key:latest,RESEND_API_KEY=resend-api-key:latest" \
            --set-env-vars "DEBUG=False,ALLOWED_HOSTS=.run.app"
```

### Step 3: Test Deployment

1. Push to master branch, or
2. Go to **Actions** → **Deploy to Cloud Run** → **Run workflow**

---

## Troubleshooting

### Error: "Invalid value for audience"

**Cause**: `GCP_WIF_PROVIDER` secret has wrong value (possibly swapped with SA email)

**Fix**:
```bash
# Get correct provider path
gcloud iam workload-identity-pools providers describe github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --format="value(name)"
```
Update GitHub secret with this exact value.

### Error: "Secret not found"

**Cause**: Secret names don't match between workflow and GCP

**Fix**: Check secret names in GCP:
```bash
gcloud secrets list
```
Ensure workflow uses exact same names (case-sensitive).

### Error: "Forbidden" (403)

**Cause**: Service not publicly accessible

**Fix**:
```bash
gcloud run services add-iam-policy-binding nova-vtu \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

### Error: "Service Unavailable" (503)

**Cause**: Application crash (check logs)

**Fix**:
```bash
# View logs
gcloud run services logs read nova-vtu --region=us-central1 --limit=50
```

Common causes:
- Invalid DATABASE_URL format
- Missing required environment variable
- Python/Django error in startup

### Error: "Permission denied" on secrets

**Cause**: Service account lacks access

**Fix**:
```bash
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:github-actions-deployer@your-project-id.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### View Deployment Logs

```bash
# Stream live logs
gcloud run services logs tail nova-vtu --region=us-central1

# View recent logs
gcloud run services logs read nova-vtu --region=us-central1 --limit=100
```

### Update a Secret Value

```bash
# Update existing secret
echo -n "new-value-here" | \
  gcloud secrets versions add SECRET_NAME --data-file=-

# Redeploy to pick up new secret
gcloud run services update nova-vtu --region=us-central1
```

---

## Quick Reference

### Key Commands

```bash
# Check current project
gcloud config get-value project

# List Cloud Run services
gcloud run services list

# Get service URL
gcloud run services describe nova-vtu --region=us-central1 --format="value(status.url)"

# View service details
gcloud run services describe nova-vtu --region=us-central1

# List secrets
gcloud secrets list

# View secret value
gcloud secrets versions access latest --secret=SECRET_NAME

# List service accounts
gcloud iam service-accounts list

# View WIF pools
gcloud iam workload-identity-pools list --location=global

# Force redeploy
gcloud run services update nova-vtu --region=us-central1
```

### Important URLs

- Cloud Run Console: `https://console.cloud.google.com/run`
- Secret Manager: `https://console.cloud.google.com/security/secret-manager`
- IAM: `https://console.cloud.google.com/iam-admin`
- Workload Identity: `https://console.cloud.google.com/iam-admin/workload-identity-pools`
- Service URL: `https://your-service-xxxxxx-uc.a.run.app`

### GitHub Secrets Summary

| Secret | Example Value |
|--------|---------------|
| `GCP_PROJECT_ID` | `your-project-id` |
| `GCP_SA_EMAIL` | `github-actions-deployer@your-project-id.iam.gserviceaccount.com` |
| `GCP_WIF_PROVIDER` | `projects/123456789012/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |

### GCP Secrets Summary

| Secret Name (lowercase) | Maps to Env Var |
|-------------------------|-----------------|
| `django-secret-key` | `SECRET_KEY` |
| `database-url` | `DATABASE_URL` |
| `paystack-secret-key` | `PAYSTACK_SECRET_KEY` |
| `paystack-public-key` | `PAYSTACK_PUBLIC_KEY` |
| `vtpass-api-key` | `VTPASS_API_KEY` |
| `vtpass-secret-key` | `VTPASS_SECRET_KEY` |
| `resend-api-key` | `RESEND_API_KEY` |
