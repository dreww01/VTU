# 🚀 Nova VTU - Pre-Deployment Checklist

**Project**: Nova VTU MVP
**Version**: 0.1.0
**Target**: Production Hosting
**Date**: 2024-12-22

---

## ✅ Code Readiness

### Files to Commit (Ready)
- [x] Dockerfile - Production build configured
- [x] docker-compose.yml - Multi-service orchestration
- [x] .env.example - Environment template
- [x] .gitignore - Excludes sensitive files
- [x] DEPLOYMENT.md - Complete deployment guide
- [x] nginx/ - Reverse proxy configuration
- [x] scripts/backup/ - Database backup automation
- [x] .github/ - CI/CD workflows (if configured)
- [x] config/middleware.py - Rate limiting
- [x] templates/errors/ - Custom error pages

### What NOT to Commit
- [ ] .env (contains secrets) ✓ Already in .gitignore
- [ ] db.sqlite3 (local database) ✓ Already in .gitignore
- [ ] staticfiles/ (generated) ✓ Already in .gitignore
- [ ] media/ (user uploads) ✓ Already in .gitignore
- [ ] __pycache__/ ✓ Already in .gitignore

---

## 🔐 Security Checklist

### Before Going Live

#### 1. Environment Variables (.env on server)
- [ ] Generate new `SECRET_KEY` (50+ chars)
  ```bash
  python3 -c "from secrets import token_urlsafe; print(token_urlsafe(50))"
  ```
- [ ] Set `DEBUG=False`
- [ ] Set `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`
- [ ] Set `CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com`

#### 2. Database
- [ ] Change PostgreSQL password in docker-compose.yml (from `nova_vtu_password`)
- [ ] Update `DATABASE_URL` in .env to match new password

#### 3. Payment & API Keys (PRODUCTION)
- [ ] Replace Paystack test keys with LIVE keys (`sk_live_*`, `pk_live_*`)
- [ ] Replace VTPass sandbox URL with production (`https://vtpass.com/api`)
- [ ] Replace VTPass test credentials with production keys
- [ ] Update Resend API key with production key
- [ ] Update `DEFAULT_FROM_EMAIL` to your verified domain

#### 4. SSL/HTTPS
- [ ] Domain DNS points to server IP (A record)
- [ ] WWW subdomain configured (CNAME or A record)
- [ ] Follow SSL setup in DEPLOYMENT.md (Let's Encrypt)

#### 5. Security Headers
Your app already includes:
- ✅ HTTPS redirect (when DEBUG=False)
- ✅ Secure cookies
- ✅ HSTS headers
- ✅ X-Frame-Options: DENY
- ✅ X-Content-Type-Nosniff
- ✅ Rate limiting middleware

---

## 📦 Hosting Platform Options

### Recommended for MVP:

#### **Option 1: Railway.app** (Easiest)
- **Pros**: Auto-deploy from GitHub, free tier, PostgreSQL included
- **Cons**: Limited free credits
- **Setup**: Connect GitHub → Deploy
- **Cost**: ~$5-10/month after free tier

#### **Option 2: Render.com**
- **Pros**: Free tier, automatic HTTPS, PostgreSQL included
- **Cons**: Slower cold starts on free tier
- **Setup**: Connect GitHub → Deploy
- **Cost**: Free tier available, $7/month for paid

#### **Option 3: DigitalOcean App Platform**
- **Pros**: Managed platform, scalable, good docs
- **Cons**: No free tier
- **Setup**: Connect GitHub → Deploy
- **Cost**: ~$12/month (Basic + Database)

#### **Option 4: VPS (DigitalOcean/Linode/Vultr)**
- **Pros**: Full control, cost-effective at scale
- **Cons**: Manual setup, maintenance responsibility
- **Setup**: Use your DEPLOYMENT.md guide
- **Cost**: $6-12/month for VPS

#### **Option 5: AWS Lightsail/EC2**
- **Pros**: AWS ecosystem, scalable
- **Cons**: Complex pricing, learning curve
- **Cost**: ~$5-15/month

---

## 🚦 Pre-Launch Testing

### On Production Server (After Deployment)

#### 1. Application Health
```bash
# Check all services running
docker compose ps

# Check health endpoint
curl https://yourdomain.com/health/

# Check SSL certificate
curl -I https://yourdomain.com
```

#### 2. Database
```bash
# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser

# Verify database connection
docker compose exec web python manage.py dbshell
```

#### 3. Static Files
```bash
# Verify static files collected
docker compose exec nginx ls -la /app/staticfiles/

# Test admin panel
https://yourdomain.com/admin/
```

#### 4. Payment Integration (CRITICAL)
- [ ] Test Paystack payment flow (use test card: 4084084084084081)
- [ ] Verify webhook receives payment confirmation
- [ ] Confirm wallet balance updates
- [ ] Test transaction history display

#### 5. VTU Services (CRITICAL)
- [ ] Test airtime purchase (small amount)
- [ ] Test data bundle purchase
- [ ] Test electricity payment
- [ ] Verify meter number validation
- [ ] Check email confirmations sent
- [ ] Verify transaction receipts

#### 6. Security
```bash
# Run Django security check
docker compose exec web python manage.py check --deploy

# Verify no DEBUG=True
curl https://yourdomain.com/nonexistent-page
# Should see custom 404, not Django debug page
```

---

## 📊 Monitoring Setup

### After Launch

#### 1. Error Tracking
- [ ] Set up Sentry (optional but recommended)
  ```python
  # Add to config/settings.py for production
  import sentry_sdk
  sentry_sdk.init(dsn="your-sentry-dsn")
  ```

#### 2. Uptime Monitoring
- [ ] Set up UptimeRobot or similar (free)
- [ ] Monitor: `https://yourdomain.com/health/`
- [ ] Alert email if down

#### 3. Logs
```bash
# View application logs
docker compose logs -f web

# View Nginx access logs
docker compose logs -f nginx

# View database logs
docker compose logs -f db
```

#### 4. Backups
- [ ] Verify backup script works
  ```bash
  docker compose exec backup /scripts/backup.sh
  ```
- [ ] Set up automated backups (cron or platform feature)
- [ ] Test database restore process

---

## 🎯 Go-Live Steps

### Step-by-Step Launch Sequence

1. **Commit all changes to GitHub**
   ```bash
   git add .
   git commit -m "Production ready: MVP v0.1.0"
   git push origin master
   ```

2. **Set up hosting platform** (choose from options above)

3. **Configure environment variables** on hosting platform

4. **Deploy application**

5. **Run database migrations**

6. **Create admin user**

7. **Test all critical flows** (payments, VTU purchases)

8. **Configure domain and SSL**

9. **Set up monitoring and backups**

10. **Go live!** 🎉

---

## 📝 Post-Launch Tasks

### Week 1
- [ ] Monitor error logs daily
- [ ] Test all features in production
- [ ] Verify payment settlements with Paystack
- [ ] Check VTPass transaction reconciliation
- [ ] Monitor server resources (CPU, RAM, Disk)

### Week 2
- [ ] Review user feedback
- [ ] Fix any bugs discovered
- [ ] Optimize slow queries if any
- [ ] Plan feature enhancements

### Ongoing
- [ ] Weekly database backups verification
- [ ] Monthly security updates (`docker compose pull`)
- [ ] SSL certificate auto-renewal (Let's Encrypt handles this)
- [ ] Monitor fraud detection logs

---

## 🆘 Emergency Contacts & Resources

### Service Providers
- **Paystack Support**: support@paystack.com
- **VTPass Support**: support@vtpass.com
- **Resend Support**: support@resend.com

### Documentation
- **Django Deployment**: https://docs.djangoproject.com/en/5.0/howto/deployment/
- **WhiteNoise**: https://whitenoise.readthedocs.io/
- **Docker**: https://docs.docker.com/

### Your Documentation
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Complete deployment guide
- [.claude/CLAUDE.md](./.claude/CLAUDE.md) - Project context
- [.env.example](./.env.example) - Environment configuration

---

## ✅ Final Pre-Deployment Command

Before you push, verify everything:

```bash
# Check for uncommitted files
git status

# Run local tests (if you have any)
python manage.py test

# Check for security issues
python manage.py check --deploy

# Verify .env.example is up to date
cat .env.example

# Check Docker build succeeds
docker compose build
```

---

## 🎊 You're Ready!

Your Nova VTU MVP is production-ready when:
- ✅ All code committed to GitHub
- ✅ Security checklist completed
- ✅ Environment variables configured
- ✅ Hosting platform selected
- ✅ Testing plan prepared

**Next Step**: Choose your hosting platform and follow DEPLOYMENT.md

**Good luck with your launch!** 🚀
