# 🚀 ReservaFlow - Deployment Guide

Complete deployment guide for ReservaFlow restaurant reservation management system.

## 📋 Deployment Options

### 1. Docker Compose (Recommended)
### 2. Cloud Deployment (AWS/DigitalOcean/etc.)
### 3. Traditional VPS Deployment

---

## 🐳 Docker Compose Deployment

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum (4GB recommended)
- 10GB disk space

### Quick Deployment
```bash
# Clone repository
git clone https://github.com/your-username/ReservaFlow.git
cd ReservaFlow

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Deploy
docker-compose -f docker-compose.prod.yml up -d

# Setup database
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
docker-compose exec web python manage.py createsuperuser
```

### Production Docker Compose Configuration

Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  web:
    build: 
      context: ./restaurant-reservations
      dockerfile: Dockerfile.prod
    ports:
      - "80:8000"
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      - DEBUG=False
      - DJANGO_SETTINGS_MODULE=config.settings.production
    depends_on:
      - db
      - redis
    restart: unless-stopped

  frontend:
    build:
      context: ./FrontendReact
      dockerfile: Dockerfile.prod
    ports:
      - "3000:80"
    restart: unless-stopped

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      - POSTGRES_DB=reservaflow
      - POSTGRES_USER=reservaflow_user
      - POSTGRES_PASSWORD=your_secure_password
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  celery:
    build: ./restaurant-reservations
    command: celery -A config worker -l info
    volumes:
      - ./restaurant-reservations:/app
    environment:
      - DEBUG=False
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery-beat:
    build: ./restaurant-reservations
    command: celery -A config beat -l info
    volumes:
      - ./restaurant-reservations:/app
    environment:
      - DEBUG=False
    depends_on:
      - db
      - redis
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/staticfiles
      - media_volume:/media
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    depends_on:
      - web
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### Production Environment Variables

Create `.env.prod`:
```bash
# Django Settings
SECRET_KEY=your_very_secure_secret_key_here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgres://reservaflow_user:your_secure_password@db:5432/reservaflow

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Email (for notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# CORS (for frontend)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=True

# Security
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Production Dockerfiles

**Backend Dockerfile (`restaurant-reservations/Dockerfile.prod`):**
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy and install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy project
COPY . .

# Collect static files
RUN uv run python manage.py collectstatic --noinput

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
```

**Frontend Dockerfile (`FrontendReact/Dockerfile.prod`):**
```dockerfile
# Build stage
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## ☁️ Cloud Deployment

### AWS Deployment with ECS

#### Prerequisites
- AWS CLI configured
- ECS CLI installed
- Domain name (optional but recommended)

#### Step 1: Create ECS Cluster
```bash
# Create cluster
aws ecs create-cluster --cluster-name reservaflow-cluster

# Create task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### Step 2: Task Definition (`task-definition.json`)
```json
{
  "family": "reservaflow",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "reservaflow-web",
      "image": "your-account.dkr.ecr.region.amazonaws.com/reservaflow:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DEBUG",
          "value": "False"
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:reservaflow-secrets-xxxxx:SECRET_KEY::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/reservaflow",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Step 3: Create Service
```bash
aws ecs create-service \
    --cluster reservaflow-cluster \
    --service-name reservaflow-service \
    --task-definition reservaflow:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### DigitalOcean App Platform

Create `app.yaml`:
```yaml
name: reservaflow
services:
- name: web
  source_dir: restaurant-reservations
  github:
    repo: your-username/ReservaFlow
    branch: main
  run_command: gunicorn --worker-tmp-dir /dev/shm config.wsgi
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  routes:
  - path: /api
  envs:
  - key: DEBUG
    value: "False"
  - key: SECRET_KEY
    value: "your-secret-key"
    type: SECRET

- name: frontend
  source_dir: FrontendReact
  github:
    repo: your-username/ReservaFlow
    branch: main
  build_command: npm run build
  environment_slug: node-js
  instance_count: 1
  instance_size_slug: basic-xxs
  routes:
  - path: /

databases:
- name: reservaflow-db
  engine: PG
  version: "15"
  size: db-s-1vcpu-1gb

workers:
- name: celery-worker
  source_dir: restaurant-reservations
  github:
    repo: your-username/ReservaFlow
    branch: main
  run_command: celery -A config worker -l info
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
```

---

## 🖥️ Traditional VPS Deployment

### Prerequisites
- Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- 2GB RAM minimum
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Nginx

### Step 1: Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm postgresql redis-server nginx certbot python3-certbot-nginx

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Database Setup
```bash
# Configure PostgreSQL
sudo -u postgres psql
CREATE DATABASE reservaflow;
CREATE USER reservaflow_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE reservaflow TO reservaflow_user;
\q
```

### Step 3: Application Deployment
```bash
# Create application directory
sudo mkdir -p /var/www/reservaflow
cd /var/www/reservaflow

# Clone repository
sudo git clone https://github.com/your-username/ReservaFlow.git .
sudo chown -R www-data:www-data /var/www/reservaflow

# Setup backend
cd restaurant-reservations
sudo -u www-data uv sync
sudo -u www-data uv run python manage.py migrate
sudo -u www-data uv run python manage.py collectstatic --noinput

# Setup frontend
cd ../FrontendReact
sudo -u www-data npm install
sudo -u www-data npm run build
```

### Step 4: Service Configuration

**Systemd service (`/etc/systemd/system/reservaflow.service`):**
```ini
[Unit]
Description=ReservaFlow Django Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/reservaflow/restaurant-reservations
Environment=PATH=/var/www/reservaflow/restaurant-reservations/.venv/bin
ExecStart=/var/www/reservaflow/restaurant-reservations/.venv/bin/gunicorn --bind unix:/run/reservaflow.sock config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Celery service (`/etc/systemd/system/celery.service`):**
```ini
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/reservaflow/restaurant-reservations
Environment=PATH=/var/www/reservaflow/restaurant-reservations/.venv/bin
ExecStart=/var/www/reservaflow/restaurant-reservations/.venv/bin/celery -A config worker --detach
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Step 5: Nginx Configuration

**Nginx config (`/etc/nginx/sites-available/reservaflow`):**
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Frontend
    location / {
        root /var/www/reservaflow/FrontendReact/build;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://unix:/run/reservaflow.sock;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Admin
    location /admin/ {
        proxy_pass http://unix:/run/reservaflow.sock;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /var/www/reservaflow/restaurant-reservations/staticfiles/;
    }

    # Media files
    location /media/ {
        alias /var/www/reservaflow/restaurant-reservations/media/;
    }
}
```

### Step 6: Enable Services
```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable reservaflow celery
sudo systemctl start reservaflow celery

# Enable Nginx site
sudo ln -s /etc/nginx/sites-available/reservaflow /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx

# Setup SSL with Let's Encrypt
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 🔒 Security Considerations

### SSL/TLS Configuration
```bash
# Generate strong DH parameters
sudo openssl dhparam -out /etc/nginx/dhparam.pem 2048

# Update Nginx config with SSL settings
# Add to server block:
# ssl_protocols TLSv1.2 TLSv1.3;
# ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:...
# ssl_dhparam /etc/nginx/dhparam.pem;
```

### Firewall Configuration
```bash
# UFW (Ubuntu)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Fail2Ban for SSH protection
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### Database Security
```bash
# PostgreSQL security
sudo -u postgres psql
ALTER USER reservaflow_user SET default_transaction_isolation TO 'read committed';
ALTER USER reservaflow_user SET timezone TO 'UTC';
\q

# Backup configuration
# Add to crontab: 0 2 * * * pg_dump reservaflow > /backups/reservaflow-$(date +\%Y\%m\%d).sql
```

---

## 📊 Monitoring and Logging

### Application Monitoring
```python
# Add to Django settings
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/reservaflow/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Health Checks
```bash
# Create health check script
cat > /usr/local/bin/reservaflow-health.sh << 'EOF'
#!/bin/bash
curl -f http://localhost/api/health/ || exit 1
systemctl is-active --quiet reservaflow || exit 1
systemctl is-active --quiet celery || exit 1
EOF

chmod +x /usr/local/bin/reservaflow-health.sh

# Add to crontab
# */5 * * * * /usr/local/bin/reservaflow-health.sh
```

---

## 🔄 Backup and Recovery

### Database Backup
```bash
# Automated backup script
cat > /usr/local/bin/backup-reservaflow.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U reservaflow_user -h localhost reservaflow > /backups/reservaflow_$DATE.sql
find /backups -name "reservaflow_*.sql" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/backup-reservaflow.sh

# Add to crontab (daily backups)
# 0 2 * * * /usr/local/bin/backup-reservaflow.sh
```

### Application Backup
```bash
# Full application backup
tar -czf /backups/reservaflow-app-$(date +%Y%m%d).tar.gz \
    /var/www/reservaflow \
    --exclude=node_modules \
    --exclude=.git \
    --exclude=*.pyc
```

### Recovery Procedures
```bash
# Database recovery
psql -U reservaflow_user -h localhost reservaflow < /backups/reservaflow_backup.sql

# Application recovery
tar -xzf /backups/reservaflow-app-backup.tar.gz -C /
sudo systemctl restart reservaflow celery nginx
```

---

## 🚀 Performance Optimization

### Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_reservations_date ON reservations(reservation_date);
CREATE INDEX CONCURRENTLY idx_reservations_status ON reservations(status);
CREATE INDEX CONCURRENTLY idx_customers_email ON customers(email);
```

### Caching Configuration
```python
# Redis cache settings
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

### Nginx Optimization
```nginx
# Add to http block
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

# Add to server block
expires 1y;
add_header Cache-Control "public, immutable";
```

---

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] Database credentials set
- [ ] SSL certificates ready
- [ ] Domain DNS configured
- [ ] Backup strategy planned
- [ ] Monitoring tools configured

### Deployment
- [ ] Application deployed
- [ ] Database migrations run
- [ ] Static files collected
- [ ] Services started and enabled
- [ ] SSL configured
- [ ] Firewall configured

### Post-Deployment
- [ ] Health checks passing
- [ ] SSL certificate valid
- [ ] Backups working
- [ ] Monitoring active
- [ ] Performance tests completed
- [ ] Security scan passed

### Rollback Plan
1. Keep previous deployment available
2. Database backup before migration
3. Quick rollback commands documented
4. Monitoring for issues post-deployment

---

## 📞 Troubleshooting

### Common Issues

**Static files not loading:**
```bash
# Check static file configuration
python manage.py collectstatic --noinput
sudo chown -R www-data:www-data /var/www/reservaflow/staticfiles
```

**Celery not processing tasks:**
```bash
# Check Celery worker status
sudo systemctl status celery
celery -A config inspect active
```

**Database connection errors:**
```bash
# Test database connection
sudo -u postgres psql -h localhost -U reservaflow_user reservaflow
```

**Frontend not loading:**
```bash
# Check build output
npm run build
sudo nginx -t && sudo systemctl reload nginx
```

For more detailed troubleshooting, check the application logs:
- Django: `/var/log/reservaflow/django.log`
- Nginx: `/var/log/nginx/error.log`
- PostgreSQL: `/var/log/postgresql/postgresql-15-main.log`

---

**🎉 Deployment Complete!** 

Your ReservaFlow application should now be running in production. Monitor the logs and health checks to ensure everything is working correctly.