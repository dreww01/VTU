# Getting Started with GCP Deployment

**Congratulations!** Your Nova VTU app is now ready for Google Cloud Platform deployment.

## 🎉 What's Been Set Up

We've prepared everything you need to deploy to GCP:

### 1. **Docker Configuration** ✅
- **[Dockerfile](../../Dockerfile)** - Updated for Cloud Run compatibility with PORT environment variable
- **[.dockerignore](../../.dockerignore)** - Optimized to exclude unnecessary files from build

### 2. **Production Dependencies** ✅
- **[pyproject.toml](../../pyproject.toml)** - Added production packages:
  - `gunicorn` - Production WSGI server
  - `google-cloud-storage` - For Cloud Storage integration
  - `django-storages[google]` - Django GCS backend

### 3. **Deployment Documentation** ✅
We created **4 comprehensive guides** in `.claude/deployment/`:

| File | Purpose | When to Use |
|------|---------|-------------|
| **[README.md](.claude/deployment/README.md)** | Navigation hub | Start here to choose your path |
| **[quick-start.md](quick-start.md)** | 30-min deploy guide | When you want to deploy FAST |
| **[gcp-deployment.md](gcp-deployment.md)** | Complete reference | For detailed understanding |
| **[local-testing.md](local-testing.md)** | Docker testing guide | Before GCP deployment |

### 4. **Settings Already Production-Ready** ✅
Your [config/settings.py](../../config/settings.py) is already configured with:
- Environment variable support
- PostgreSQL via `DATABASE_URL`
- WhiteNoise for static files
- Production security settings
- Cloud SQL compatibility

---

## 🚀 Your Next Steps

### Option 1: Quick Deploy (30 minutes)

**Best for:** Getting your app live quickly

```bash
# 1. Navigate to quick start guide
cd .claude/deployment
cat quick-start.md

# 2. Follow the step-by-step commands
# All commands are ready to copy-paste!
```

### Option 2: Test Locally First (Recommended)

**Best for:** Catching issues before deployment

```bash
# 1. Test Docker locally
docker build -t nova-vtu:test .
docker run -p 8080:8080 \
  -e SECRET_KEY="test-key" \
  -e DEBUG="True" \
  nova-vtu:test

# 2. Visit http://localhost:8080
# 3. Once working, proceed to GCP deployment
```

### Option 3: Learn While Deploying

**Best for:** Understanding the full stack

1. Read [gcp-deployment.md](gcp-deployment.md) from top to bottom
2. Test locally using [local-testing.md](local-testing.md)
3. Deploy using commands from [quick-start.md](quick-start.md)

---

## 📋 Pre-Deployment Checklist

Before you deploy, make sure you have:

### Required Accounts
- [ ] Google Cloud account ([console.cloud.google.com](https://console.cloud.google.com))
- [ ] Billing enabled on GCP
- [ ] Paystack account with production keys
- [ ] VTPass account with production API credentials
- [ ] Resend account for emails

### Required Tools
- [ ] `gcloud` CLI installed
- [ ] Docker installed (optional, for local testing)
- [ ] Git (already have this)

### Required Information
- [ ] Domain name (optional but recommended)
- [ ] All API keys documented and ready

### Install gcloud CLI

**macOS/Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud --version
```

**Windows:**
Download from: https://cloud.google.com/sdk/docs/install

---

## 🎯 Learning Path for GCP

Over the next few days, here's what you'll learn:

### Day 1-2: GCP Fundamentals
- [ ] Create GCP account and project
- [ ] Learn Cloud Console navigation
- [ ] Understand billing and free tier limits
- [ ] Practice with `gcloud` CLI commands

**Resources:**
- [GCP Console](https://console.cloud.google.com)
- [Quick Start Guide](quick-start.md)

### Day 3-4: Cloud Run + Docker
- [ ] Test your app locally with Docker
- [ ] Understand containerization
- [ ] Deploy to Cloud Run
- [ ] Configure environment variables

**Resources:**
- [Local Testing Guide](local-testing.md)
- [Cloud Run Docs](https://cloud.google.com/run/docs)

### Day 5-6: Cloud SQL + Database
- [ ] Set up PostgreSQL instance
- [ ] Configure database connections
- [ ] Run migrations in production
- [ ] Understand Cloud SQL Proxy

**Resources:**
- Section in [GCP Deployment Guide](gcp-deployment.md#database-setup)

### Day 7: Static Files + Domain
- [ ] Configure Cloud Storage for media
- [ ] Set up custom domain
- [ ] Enable HTTPS/SSL
- [ ] Test everything end-to-end

**Resources:**
- [Custom Domain Setup](gcp-deployment.md#custom-domain--ssl)

---

## 📚 Documentation Structure

```
.claude/deployment/
├── README.md                   # This directory overview (navigation hub)
├── GETTING-STARTED.md         # You are here! (orientation guide)
├── quick-start.md             # 30-minute deployment commands
├── gcp-deployment.md          # Complete GCP reference guide
└── local-testing.md           # Docker testing before deployment
```

---

## 💡 Pro Tips

### Tip 1: Start with Sandbox APIs
When first deploying, use **test/sandbox** API keys:
```env
VTPASS_BASE_URL=https://sandbox.vtpass.com/api  # Sandbox
PAYSTACK_SECRET_KEY=sk_test_...                 # Test mode
```

Switch to production keys only after testing everything works.

### Tip 2: Use Cloud Shell
Don't want to install `gcloud` locally? Use [Cloud Shell](https://shell.cloud.google.com):
- Built-in `gcloud` CLI
- Free 5GB persistent storage
- Browser-based terminal
- Perfect for quick deploys

### Tip 3: Set Budget Alerts
Avoid surprise bills:
```bash
gcloud billing budgets create \
  --billing-account=YOUR_ID \
  --display-name="Nova VTU Alert" \
  --budget-amount=30USD \
  --threshold-rule=percent=80
```

### Tip 4: Use Cloud Run Logs
Debug issues with:
```bash
gcloud run services logs tail nova-vtu --region REGION
```

---

## 🆘 Common First-Time Questions

### Q: How much will this cost?
**A:** ~$15-30/month for low-medium traffic. GCP free tier covers some usage. See [cost optimization guide](gcp-deployment.md#cost-optimization).

### Q: Do I need a domain?
**A:** No, Cloud Run provides a free URL like `https://nova-vtu-xxx.run.app`. Custom domain is optional.

### Q: Can I deploy without a credit card?
**A:** No, GCP requires billing enabled even with free tier. But you get $300 free credits.

### Q: How long does deployment take?
**A:** First time: 30-60 minutes. Future updates: ~5 minutes.

### Q: What if something goes wrong?
**A:** Check [troubleshooting section](gcp-deployment.md#troubleshooting) or review logs. Everything is reversible.

### Q: Can I test locally before deploying?
**A:** Yes! See [local-testing.md](local-testing.md) for Docker testing.

---

## 🎓 Recommended Order

For first-time GCP users:

1. **Read this file** ✅ (you're here!)
2. **Test locally** → [local-testing.md](local-testing.md)
3. **Create GCP account** → [console.cloud.google.com](https://console.cloud.google.com)
4. **Deploy with quick start** → [quick-start.md](quick-start.md)
5. **Reference full guide when needed** → [gcp-deployment.md](gcp-deployment.md)

---

## 📞 Need Help?

### Before Deploying
- Review [README.md](README.md) for overview
- Check [local-testing.md](local-testing.md) for Docker testing

### During Deployment
- Use [quick-start.md](quick-start.md) for commands
- Reference [gcp-deployment.md](gcp-deployment.md) for details

### After Deployment
- See [gcp-deployment.md#monitoring](gcp-deployment.md#monitoring--logging)
- Check [gcp-deployment.md#troubleshooting](gcp-deployment.md#troubleshooting)

### Still Stuck?
1. Check logs: `gcloud run services logs read nova-vtu`
2. Review error in [troubleshooting section](gcp-deployment.md#troubleshooting)
3. Open an issue on GitHub

---

## ✅ Ready to Deploy?

You now have everything you need:

- ✅ Docker configuration
- ✅ Production dependencies
- ✅ Comprehensive documentation
- ✅ Step-by-step guides
- ✅ Troubleshooting resources

**Your app is production-ready!**

### Next Action

Choose your path:

**Path A - Fast Track:**
```bash
cd .claude/deployment
cat quick-start.md  # Follow commands
```

**Path B - Safe Track:**
```bash
# Test locally first
docker build -t nova-vtu:test .
# Then deploy to GCP
```

**Path C - Learning Track:**
```bash
# Read complete guide
cat .claude/deployment/gcp-deployment.md
```

---

## 🚀 Let's Go!

Head to [**quick-start.md**](quick-start.md) to begin your deployment journey.

**Good luck, and happy deploying!** 🎉

---

## 📖 Additional Resources

- [GCP Free Tier](https://cloud.google.com/free) - What's free
- [Cloud Run Pricing](https://cloud.google.com/run/pricing) - Detailed costs
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Your Main README](../../README.md) - Project overview

---

*Last Updated: 2025-12-22*
