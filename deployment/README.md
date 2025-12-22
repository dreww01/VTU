# Nova VTU - Deployment Documentation

This directory contains everything you need to deploy Nova VTU to Google Cloud Platform.

## 📚 Documentation Files

### 1. **[quick-start.md](quick-start.md)** ⚡
**Start here if you want to deploy FAST**

- Step-by-step commands ready to copy-paste
- Deploy in ~30 minutes
- Minimal explanations, maximum action
- All commands in sequence
- Perfect for: Getting your app live quickly

### 2. **[gcp-deployment.md](gcp-deployment.md)** 📖
**Complete reference guide**

- Comprehensive GCP deployment guide
- Detailed explanations for each step
- Troubleshooting section
- Cost optimization tips
- Monitoring and alerts setup
- Custom domain configuration
- Perfect for: Understanding what you're doing and production setup

### 3. **[local-testing.md](local-testing.md)** 🧪
**Test before you deploy**

- Test Docker setup locally
- Docker Compose configuration
- Debugging tips
- Pre-deployment checklist
- Perfect for: Catching issues before GCP deployment

---

## 🚀 Deployment Path

Choose your path based on experience level:

### Path A: Quick Deploy (Recommended for first deployment)
```
1. Read quick-start.md
2. Follow commands step-by-step
3. Test your deployment
4. Reference gcp-deployment.md if you hit issues
```

### Path B: Thorough Deploy (Recommended for production)
```
1. Test locally using local-testing.md
2. Read gcp-deployment.md sections you need
3. Use quick-start.md commands
4. Set up monitoring and alerts from gcp-deployment.md
```

### Path C: Learning Deploy
```
1. Read gcp-deployment.md completely
2. Test locally with local-testing.md
3. Deploy using quick-start.md for speed
4. Configure advanced features from gcp-deployment.md
```

---

## ✅ Pre-Deployment Checklist

Before you start:

### Accounts & Access
- [ ] Google Cloud account created
- [ ] Billing enabled on GCP
- [ ] `gcloud` CLI installed
- [ ] Docker installed (for local testing)

### API Keys Ready
- [ ] Paystack production keys (secret & public)
- [ ] VTPass production API credentials
- [ ] Resend API key for emails
- [ ] Domain name (optional but recommended)

### Local Preparation
- [ ] Tested app locally
- [ ] All tests passing
- [ ] Environment variables documented
- [ ] Database migrations clean

---

## 🎯 Quick Reference

### Essential Commands

**Deploy/Update:**
```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/nova-vtu
gcloud run services update nova-vtu --region us-central1 --image gcr.io/$PROJECT_ID/nova-vtu
```

**View Logs:**
```bash
gcloud run services logs tail nova-vtu --region us-central1
```

**Check Status:**
```bash
gcloud run services describe nova-vtu --region us-central1
```

---

## 📁 Related Files

### In Root Directory

- [`Dockerfile`](../../Dockerfile) - Container configuration for Cloud Run
- [`.dockerignore`](../../.dockerignore) - Files excluded from container
- [`pyproject.toml`](../../pyproject.toml) - Python dependencies (includes production deps)

### Django Configuration

- [`config/settings.py`](../../config/settings.py) - Already configured for GCP with environment variables

---

## 🆘 Need Help?

### Common Issues

| Issue | Solution |
|-------|----------|
| Build fails | Check [local-testing.md](local-testing.md#common-local-issues) |
| Database connection | See [gcp-deployment.md](gcp-deployment.md#troubleshooting) |
| 502 errors | Check logs: `gcloud run services logs read nova-vtu` |
| Static files 404 | Verify collectstatic ran in Dockerfile |
| CSRF errors | Update CSRF_TRUSTED_ORIGINS |

### Getting Support

1. **Check logs first**: `gcloud run services logs tail nova-vtu --region REGION`
2. **Review troubleshooting**: [gcp-deployment.md#troubleshooting](gcp-deployment.md#troubleshooting)
3. **Test locally**: Use [local-testing.md](local-testing.md) to reproduce
4. **GCP Support**: https://cloud.google.com/support

---

## 💰 Cost Estimate

**Monthly costs for low-medium traffic:**

| Service | Tier | Cost |
|---------|------|------|
| Cloud Run | Free tier + usage | $5-15 |
| Cloud SQL | db-f1-micro | $7-10 |
| Cloud Storage | Standard | $1-5 |
| **Total** | | **~$15-30** |

See [gcp-deployment.md#cost-optimization](gcp-deployment.md#cost-optimization) for ways to reduce costs.

---

## 🔐 Security Notes

### Secrets Management
- **Never** commit secrets to git
- Use GCP Secret Manager (configured in quick-start)
- Rotate keys regularly
- Use different keys for dev/staging/prod

### Production Settings
```bash
DEBUG=False  # Always!
SECRET_KEY=<strong-random-key>
ALLOWED_HOSTS=<your-domain>
CSRF_TRUSTED_ORIGINS=https://<your-domain>
```

---

## 🎓 Learning Resources

### GCP Official Docs
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [Django on Cloud Run](https://cloud.google.com/python/django/run)

### Django Production
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Security Settings](https://docs.djangoproject.com/en/stable/topics/security/)

---

## 📊 Deployment Timeline

**Total time: 30-60 minutes** (for first deployment)

1. **GCP Setup** (10 min)
   - Create project, enable APIs

2. **Database** (10 min)
   - Cloud SQL instance creation (most of this is waiting)

3. **Secrets** (5 min)
   - Configure all secrets in Secret Manager

4. **Build & Deploy** (10 min)
   - Docker build and Cloud Run deployment

5. **Post-Deploy** (5-10 min)
   - Migrations, superuser, testing

**Subsequent deployments: ~5 minutes**

---

## ✨ What You Get

After successful deployment:

- ✅ **Live URL**: `https://YOUR-SERVICE.run.app`
- ✅ **Automatic HTTPS**: SSL certificate included
- ✅ **Auto-scaling**: Scales to zero when idle
- ✅ **Database**: Managed PostgreSQL with backups
- ✅ **Storage**: Google Cloud Storage for media
- ✅ **Monitoring**: Cloud Logging & Monitoring
- ✅ **Security**: Secrets in Secret Manager
- ✅ **99.95% SLA**: Cloud Run reliability guarantee

---

## 🔄 Next Steps After Deployment

1. **Custom Domain**: Configure your domain ([guide](gcp-deployment.md#custom-domain--ssl))
2. **Monitoring**: Set up alerts ([guide](gcp-deployment.md#monitoring--logging))
3. **CI/CD**: Automate deployments with GitHub Actions
4. **Backups**: Verify Cloud SQL backups are enabled
5. **Load Testing**: Test under expected traffic
6. **Documentation**: Document your specific setup

---

## 📝 Deployment Log Template

Keep track of your deployment:

```markdown
## Deployment Log

**Date**: 2025-XX-XX
**Project ID**: nova-vtu-prod
**Region**: us-central1
**Database Instance**: nova-vtu-db

### URLs
- Cloud Run: https://YOUR-SERVICE.run.app
- Custom Domain: https://yourdomain.com
- Admin: https://yourdomain.com/admin/

### Credentials
- Database User: django
- Database Name: novavtu
- GCS Bucket: PROJECT-ID-media

### Secrets
- [x] django-secret-key
- [x] database-url
- [x] paystack-secret-key
- [x] paystack-public-key
- [x] vtpass-api-key
- [x] vtpass-secret-key
- [x] resend-api-key

### Post-Deployment
- [x] Migrations run
- [x] Superuser created
- [x] Paystack webhook updated
- [x] Test transaction completed
- [x] Email sending verified
```

---

**Ready to deploy? Start with [quick-start.md](quick-start.md)! 🚀**
