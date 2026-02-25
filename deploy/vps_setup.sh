#!/usr/bin/env bash
# =============================================================
# MIBSP VPS Auto-Deployment Script
# Municipal Integrity & Bribe-Free Service Portal
# Usage: bash vps_setup.sh
# Tested on: Ubuntu 22.04 LTS
# =============================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration (can be overridden via environment variables)
REPO_URL="${REPO_URL:-https://github.com/yourusername/mibsp.git}"
DOMAIN="${DOMAIN:-yourdomain.com}"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 32)}"
APP_DIR="/var/www/mibsp"

# Logging functions
log_info() {
    echo -e "${BLUE}▶${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# ── 1. System Update ─────────────────────────────────────────
update_system() {
    log_info "Updating system packages..."
    apt update && apt upgrade -y
    log_success "System updated"
}

# ── 2. Install Dependencies ───────────────────────────────────
install_dependencies() {
    log_info "Installing dependencies..."
    apt install -y \
        python3 python3-pip python3-venv python3-dev \
        nginx \
        mysql-server libmysqlclient-dev \
        redis-server \
        certbot python3-certbot-nginx \
        git ufw fail2ban \
        supervisor \
        build-essential pkg-config \
        curl wget
    log_success "Dependencies installed"
}

# ── 3. Firewall Setup ─────────────────────────────────────────
setup_firewall() {
    log_info "Configuring firewall..."
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow OpenSSH
    ufw allow 'Nginx Full'
    ufw --force enable
    log_success "Firewall configured"
}

# ── 4. MySQL Setup ────────────────────────────────────────────
setup_mysql() {
    log_info "Configuring MySQL..."
    
    # Start MySQL if not running
    systemctl start mysql
    systemctl enable mysql
    
    # Create database and user
    mysql -e "CREATE DATABASE IF NOT EXISTS mibsp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    mysql -e "CREATE USER IF NOT EXISTS 'mibsp_user'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';"
    mysql -e "GRANT ALL PRIVILEGES ON mibsp.* TO 'mibsp_user'@'localhost';"
    mysql -e "FLUSH PRIVILEGES;"
    
    log_success "MySQL configured"
    log_info "Database: mibsp"
    log_info "User: mibsp_user"
    log_info "Password: ${DB_PASSWORD}"
}

# ── 5. Clone & Setup Application ──────────────────────────────
setup_application() {
    log_info "Setting up application..."
    
    # Create app directory
    mkdir -p /var/www
    cd /var/www
    
    # Clone repository (or create if local)
    if [[ -d "mibsp" ]]; then
        log_warning "Directory exists, pulling latest changes..."
        cd mibsp
        git pull || true
    else
        git clone "${REPO_URL}" mibsp || {
            log_warning "Git clone failed, creating directory structure..."
            mkdir -p mibsp
        }
        cd mibsp
    fi
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    pip install -r requirements.txt
    pip install gunicorn pymysql
    
    log_success "Application setup complete"
}

# ── 6. Create Environment File ────────────────────────────────
create_env() {
    log_info "Creating environment file..."
    
    # Generate secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    cat > .env << EOF
# MIBSP Environment Configuration
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_USER=mibsp_user
MYSQL_PASSWORD=${DB_PASSWORD}
MYSQL_DB=mibsp

# File Uploads
UPLOAD_FOLDER=/var/www/mibsp/uploads
MAX_CONTENT_LENGTH=16777216

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Session
SESSION_LIFETIME_HOURS=8
EOF
    
    # Secure the env file
    chmod 600 .env
    chown www-data:www-data .env
    
    log_success "Environment file created"
}

# ── 7. Initialize Database ────────────────────────────────────
init_database() {
    log_info "Initializing database..."
    
    source venv/bin/activate
    
    # Create database tables
    flask db upgrade || {
        log_warning "Flask migrate not initialized, creating tables..."
        python3 -c "
from app import create_app, db
from app.models import Department, Service, User
app = create_app('production')
with app.app_context():
    db.create_all()
"
    }
    
    # Seed with demo data
    python seed.py || log_warning "Seed script failed or not found"
    
    log_success "Database initialized"
}

# ── 8. Create Gunicorn Systemd Service ────────────────────────
create_gunicorn_service() {
    log_info "Creating Gunicorn service..."
    
    # Create log directory
    mkdir -p /var/log/mibsp
    chown www-data:www-data /var/log/mibsp
    
    cat > /etc/systemd/system/mibsp.service << 'EOF'
[Unit]
Description=MIBSP Gunicorn Application Server
After=network.target mysql.service redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/mibsp
Environment="PATH=/var/www/mibsp/venv/bin"
EnvironmentFile=/var/www/mibsp/.env
ExecStart=/var/www/mibsp/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --access-logfile /var/log/mibsp/access.log \
    --error-logfile /var/log/mibsp/error.log \
    --capture-output \
    --enable-stdio-inheritance \
    wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable mibsp
    
    log_success "Gunicorn service created"
}

# ── 9. Configure Nginx ────────────────────────────────────────
configure_nginx() {
    log_info "Configuring Nginx..."
    
    cat > /etc/nginx/sites-available/mibsp << EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # File upload limit
    client_max_body_size 16M;
    
    # Static files
    location /static/ {
        alias /var/www/mibsp/app/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
    
    # Uploads - internal only
    location /uploads/ {
        internal;
        alias /var/www/mibsp/uploads/;
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }
}
EOF
    
    # Enable site
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/mibsp /etc/nginx/sites-enabled/mibsp
    
    # Test and reload
    nginx -t && systemctl reload nginx
    systemctl enable nginx
    
    log_success "Nginx configured"
}

# ── 10. Setup SSL with Let's Encrypt ──────────────────────────
setup_ssl() {
    log_info "Setting up SSL certificate..."
    
    if [[ "${DOMAIN}" != "yourdomain.com" ]]; then
        certbot --nginx -d "${DOMAIN}" -d "www.${DOMAIN}" --non-interactive --agree-tos --email "admin@${DOMAIN}" || {
            log_warning "SSL setup failed. You can run 'certbot --nginx' manually later."
        }
        log_success "SSL certificate installed"
    else
        log_warning "Domain not configured. Skipping SSL setup."
        log_info "Run: certbot --nginx -d yourdomain.com after configuring DNS"
    fi
}

# ── 11. Configure Celery with Supervisor ─────────────────────
setup_celery() {
    log_info "Configuring Celery..."
    
    cat > /etc/supervisor/conf.d/mibsp_celery.conf << 'EOF'
[program:mibsp_celery]
command=/var/www/mibsp/venv/bin/celery -A app.celery worker --loglevel=info --concurrency=2
 directory=/var/www/mibsp
user=www-data
autostart=true
autorestart=true
stopwaitsecs=600
killasgroup=true
priority=998
environment=PATH="/var/www/mibsp/venv/bin",FLASK_ENV="production"
stdout_logfile=/var/log/mibsp/celery.log
stderr_logfile=/var/log/mibsp/celery_err.log

[program:mibsp_celery_beat]
command=/var/www/mibsp/venv/bin/celery -A app.celery beat --loglevel=info
directory=/var/www/mibsp
user=www-data
autostart=true
autorestart=true
stopwaitsecs=600
killasgroup=true
priority=999
environment=PATH="/var/www/mibsp/venv/bin",FLASK_ENV="production"
stdout_logfile=/var/log/mibsp/celery_beat.log
stderr_logfile=/var/log/mibsp/celery_beat_err.log
EOF
    
    supervisorctl reread
    supervisorctl update
    
    log_success "Celery configured"
}

# ── 12. Setup Daily Backup Cron ───────────────────────────────
setup_backup() {
    log_info "Setting up daily backup..."
    
    # Create backup script
    cat > /var/www/mibsp/deploy/backup.sh << 'EOF'
#!/usr/bin/env bash
# Daily MySQL Backup for MIBSP

BACKUP_DIR="/var/backups/mibsp"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
FILENAME="mibsp_backup_${DATE}.sql.gz"

source /var/www/mibsp/.env

mkdir -p "${BACKUP_DIR}"

# Dump & compress
mysqldump \
  -u "${MYSQL_USER}" \
  -p"${MYSQL_PASSWORD}" \
  --single-transaction \
  --routines \
  --triggers \
  "${MYSQL_DB}" 2>/dev/null | gzip > "${BACKUP_DIR}/${FILENAME}"

# Keep only last 30 days
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +30 -delete

echo "Backup saved: ${BACKUP_DIR}/${FILENAME}"
EOF
    
    chmod +x /var/www/mibsp/deploy/backup.sh
    
    # Add to cron
    (crontab -l 2>/dev/null; echo "0 2 * * * /var/www/mibsp/deploy/backup.sh >> /var/log/mibsp/backup.log 2>&1") | crontab -
    
    log_success "Daily backup scheduled (2:00 AM)"
}

# ── 13. Set Permissions ───────────────────────────────────────
set_permissions() {
    log_info "Setting permissions..."
    
    # Create uploads directory
    mkdir -p /var/www/mibsp/uploads
    
    # Set ownership
    chown -R www-data:www-data /var/www/mibsp
    
    # Set directory permissions
    find /var/www/mibsp -type d -exec chmod 755 {} \;
    find /var/www/mibsp -type f -exec chmod 644 {} \;
    
    # Special permissions for sensitive files
    chmod 600 /var/www/mibsp/.env
    chmod 755 /var/www/mibsp/venv/bin/*
    
    log_success "Permissions set"
}

# ── 14. Start Services ────────────────────────────────────────
start_services() {
    log_info "Starting services..."
    
    systemctl start mibsp
    supervisorctl start mibsp_celery
    supervisorctl start mibsp_celery_beat
    
    log_success "Services started"
}

# ── 15. Print Summary ─────────────────────────────────────────
print_summary() {
    echo ""
    echo "============================================================="
    echo -e "${GREEN}          MIBSP Deployment Complete!${NC}"
    echo "============================================================="
    echo ""
    echo -e "${BLUE}Application URL:${NC} http://${DOMAIN}"
    echo -e "${BLUE}Application Directory:${NC} ${APP_DIR}"
    echo ""
    echo -e "${YELLOW}Database Credentials:${NC}"
    echo "  Database: mibsp"
    echo "  Username: mibsp_user"
    echo "  Password: ${DB_PASSWORD}"
    echo ""
    echo -e "${YELLOW}Default Admin Credentials:${NC}"
    echo "  Username: admin"
    echo "  Password: Admin@1234"
    echo ""
    echo -e "${YELLOW}Important Commands:${NC}"
    echo "  View logs: journalctl -u mibsp -f"
    echo "  Restart app: systemctl restart mibsp"
    echo "  Backup now: bash /var/www/mibsp/deploy/backup.sh"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Configure DNS to point ${DOMAIN} to this server"
    echo "  2. Run: certbot --nginx -d ${DOMAIN} (for SSL)"
    echo "  3. Change default admin password immediately"
    echo "  4. Review and update .env file if needed"
    echo ""
    echo "============================================================="
}

# Main execution
main() {
    echo "============================================================="
    echo "     MIBSP - Municipal Integrity Portal Deployment"
    echo "============================================================="
    echo ""
    
    check_root
    update_system
    install_dependencies
    setup_firewall
    setup_mysql
    setup_application
    create_env
    init_database
    create_gunicorn_service
    configure_nginx
    setup_ssl
    setup_celery
    setup_backup
    set_permissions
    start_services
    print_summary
}

# Run main function
main "$@"
