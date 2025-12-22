# Nova VTU - Deployment Guide

This guide covers deploying Nova VTU to a production server using Docker, Nginx, and Let's Encrypt SSL.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Environment Configuration](#environment-configuration)
4. [SSL Certificate Setup](#ssl-certificate-setup)
5. [Deployment Steps](#deployment-steps)
6. [Database Migration](#database-migration)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)
9. [Security Checklist](#security-checklist)

---

## Prerequisites

### Server Requirements

- **OS**: Ubuntu 22.04 LTS (recommended) or Debian 12
- **RAM**: Minimum 2GB (4GB recommended)
- **CPU**: 2 vCPUs minimum
- **Storage**: 20GB SSD minimum
- **Domain**: A registered domain pointing to your server IP

### Software Requirements

- Docker Engine 24.0+
- Docker Compose v2.20+
- Git

---

## Server Setup

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Start Docker on boot
sudo systemctl enable docker

# Log out and back in for group changes to take effect
```

### 3. Install Docker Compose

```bash
# Docker Compose is included with Docker Desktop
# For Linux servers, it's included as a Docker plugin
docker compose version
```

### 4. Configure Firewall

```bash
# Allow SSH, HTTP, and HTTPS
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 5. Clone Repository

```bash
cd /opt
sudo git clone https://github.com/dreww01/VTU.git nova-vtu
sudo chown -R $USER:$USER nova-vtu
cd nova-vtu
```

---

## Environment Configuration

### 1. Create Production Environment File

```bash
cp .env.example .env
nano .env
```

### 2. Configure Environment Variables

```bash
# =============================================================================
# PRODUCTION ENVIRONMENT - .env
# =============================================================================

# Django Settings(update domain when ready)
SECRET_KEY=your-super-secure-secret-key-generate-new-one
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database (use the docker-compose internal connection)
DATABASE_URL=postgresql://nova_vtu:nova_vtu_password@db:5432/nova_vtu

# Paystack (PRODUCTION keys - sk_live_*, pk_live_*)
PAYSTACK_SECRET_KEY=sk_live_xxxxxxxxxxxxxxxxxxxx
PAYSTACK_PUBLIC_KEY=pk_live_xxxxxxxxxxxxxxxxxxxx

# VTPass (PRODUCTION URL and keys)
VTPASS_BASE_URL=https://vtpass.com/api
VTPASS_API_KEY=your_production_api_key
VTPASS_SECRET_KEY=SK_your_production_secret_key
VTPASS_PUBLIC_KEY=PK_your_production_public_key

# Email (Resend)
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
DEFAULT_FROM_EMAIL=Nova VTU <noreply@yourdomain.com>
```

### 3. Generate Secure SECRET_KEY

```bash
python3 -c "from secrets import token_urlsafe; print(token_urlsafe(50))"
```

### 4. Update Docker Compose Database Password

Edit `docker-compose.yml` and change the default database password:

```yaml
db:
  environment:
    POSTGRES_PASSWORD: your-secure-database-password
```

Also update the `DATABASE_URL` in your `.env` file to match.

---

## SSL Certificate Setup

### 1. Update Domain in Nginx Config

```bash
# Replace 'yourdomain.com' with your actual domain
sed -i 's/yourdomain.com/your-actual-domain.com/g' nginx/conf.d/nova-vtu.conf
```

### 2. Initial Setup (Without SSL)

Create a temporary nginx config for initial certificate acquisition:

```bash
# Create temporary config for Let's Encrypt challenge
cat > nginx/conf.d/nova-vtu.conf << 'EOF'
server {
    listen 80;
    server_name your-actual-domain.com www.your-actual-domain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'Nova VTU - Setting up SSL...';
        add_header Content-Type text/plain;
    }
}
EOF
```

### 3. Start Services for Certificate Acquisition

```bash
# Start nginx and certbot containers only
docker compose up -d nginx
```

### 4. Obtain SSL Certificate

```bash
# Request certificate from Let's Encrypt
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email your-email@domain.com \
    --agree-tos \
    --no-eff-email \
    -d your-actual-domain.com \
    -d www.your-actual-domain.com
```

### 5. Restore Full Nginx Configuration

```bash
# Restore the full SSL-enabled nginx config
git checkout nginx/conf.d/nova-vtu.conf

# Update domain name again
sed -i 's/yourdomain.com/your-actual-domain.com/g' nginx/conf.d/nova-vtu.conf

# Restart nginx to apply SSL
docker compose restart nginx
```

### 6. Verify SSL Auto-Renewal

```bash
# Test renewal (dry run)
docker compose run --rm certbot renew --dry-run
```

---

## Deployment Steps

### 1. Build and Start All Services

```bash
cd /opt/nova-vtu

# Build the application image
docker compose build

# Start all services in detached mode
docker compose up -d
```

### 2. Check Service Status

```bash
# View running containers
docker compose ps

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f web
docker compose logs -f nginx
```

### 3. Verify Deployment

```bash
# Check if web service is healthy
curl -I https://your-actual-domain.com

# Check health endpoint
curl https://your-actual-domain.com/health/
```

---

## Database Migration

### 1. Run Migrations

```bash
# Apply database migrations
docker compose exec web python manage.py migrate
```

### 2. Create Superuser

```bash
# Create admin user
docker compose exec web python manage.py createsuperuser
```

### 3. Load Initial Data (if any)

```bash
# If you have fixtures
docker compose exec web python manage.py loaddata initial_data.json
```

---

## Monitoring & Maintenance

### Daily Operations

```bash
# View logs
docker compose logs -f --tail=100

# Restart services
docker compose restart

# Stop services
docker compose down

# Start services
docker compose up -d
```

### Database Backup

```bash
# Create backup script
cat > /opt/nova-vtu/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/nova-vtu/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
docker compose exec -T db pg_dump -U nova_vtu nova_vtu > $BACKUP_DIR/db_$TIMESTAMP.sql

# Compress backup
gzip $BACKUP_DIR/db_$TIMESTAMP.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_$TIMESTAMP.sql.gz"
EOF

chmod +x /opt/nova-vtu/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/nova-vtu/backup.sh") | crontab -
```

### Database Restore

```bash
# Restore from backup
gunzip -c backups/db_TIMESTAMP.sql.gz | docker compose exec -T db psql -U nova_vtu nova_vtu
```

### Update Application

```bash
cd /opt/nova-vtu

# Pull latest changes
git pull origin master

# Rebuild and restart
docker compose build
docker compose up -d

# Run migrations if needed
docker compose exec web python manage.py migrate
```

### SSL Certificate Renewal

Certificates auto-renew via the certbot container. To manually renew:

```bash
docker compose run --rm certbot renew
docker compose restart nginx
```

---

## Troubleshooting

### Container Issues

```bash
# Check container status
docker compose ps

# View container logs
docker compose logs web
docker compose logs nginx
docker compose logs db

# Restart specific service
docker compose restart web

# Rebuild and restart
docker compose up -d --build web
```

### Database Connection Issues

```bash
# Check if database is running
docker compose exec db pg_isready -U nova_vtu

# Connect to database shell
docker compose exec db psql -U nova_vtu nova_vtu

# Check database logs
docker compose logs db
```

### Nginx Issues

```bash
# Test nginx configuration
docker compose exec nginx nginx -t

# Reload nginx config
docker compose exec nginx nginx -s reload

# Check nginx access logs
docker compose exec nginx tail -f /var/log/nginx/access.log

# Check nginx error logs
docker compose exec nginx tail -f /var/log/nginx/error.log
```

### Application Issues

```bash
# Access Django shell
docker compose exec web python manage.py shell

# Check Django configuration
docker compose exec web python manage.py check --deploy

# Collect static files manually
docker compose exec web python manage.py collectstatic --noinput
```

### Common Errors

**502 Bad Gateway**
- Check if web container is running: `docker compose ps`
- Check web container logs: `docker compose logs web`
- Ensure gunicorn is starting properly

**Static files not loading**
- Run collectstatic: `docker compose exec web python manage.py collectstatic --noinput`
- Check static volume: `docker compose exec nginx ls -la /app/staticfiles/`

**SSL Certificate errors**
- Check certificate exists: `docker compose exec nginx ls -la /etc/letsencrypt/live/`
- Renew certificate: `docker compose run --rm certbot renew`

---

## Security Checklist

Before going live, verify:

- [ ] **SECRET_KEY**: Generated new secure key
- [ ] **DEBUG**: Set to `False`
- [ ] **ALLOWED_HOSTS**: Only production domain(s)
- [ ] **Database password**: Changed from default
- [ ] **API Keys**: Using production keys (Paystack, VTPass, Resend)
- [ ] **SSL**: Certificate installed and working
- [ ] **Firewall**: Only ports 80, 443, and SSH open
- [ ] **Backups**: Automated database backups configured
- [ ] **Monitoring**: Health checks enabled

### Test Security Headers

```bash
# Check security headers
curl -I https://your-actual-domain.com

# Should see:
# Strict-Transport-Security
# X-Frame-Options
# X-Content-Type-Options
# Content-Security-Policy
```

---

## Quick Reference Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f

# Restart all services
docker compose restart

# Rebuild and restart
docker compose up -d --build

# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser

# Backup database
docker compose exec -T db pg_dump -U nova_vtu nova_vtu > backup.sql

# Check deployment
docker compose exec web python manage.py check --deploy
```

---

## Support

**Repository**: [https://github.com/dreww01/VTU](https://github.com/dreww01/VTU)

For issues with deployment:
1. Check logs: `docker compose logs -f`
2. Review this guide's troubleshooting section
3. Check Django deployment checklist: `python manage.py check --deploy`
4. Open an issue on GitHub: [https://github.com/dreww01/VTU/issues](https://github.com/dreww01/VTU/issues)
