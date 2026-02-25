# 🏛️ MIBSP - Municipal Integrity & Bribe-Free Service Portal

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A **secure, anonymous, role-based municipal grievance portal** that enables citizens to report corruption and service issues without revealing their identity.

## 🌟 Features

### For Citizens
- **🔒 Complete Anonymity** - No login, no registration, no PII collection
- **📝 Easy Complaint Submission** - Simple form with department/service selection
- **🔍 Real-time Tracking** - Track complaints with unique tamper-proof IDs
- **📊 Public Dashboard** - View transparency statistics
- **📱 Mobile Responsive** - Works on all devices

### For Officers
- **📋 Department Dashboard** - View assigned complaints
- **✏️ Status Updates** - Update complaint status with notes
- **🔔 Notifications** - Get notified of new assignments
- **📈 Performance Metrics** - Track resolution statistics

### For Administrators
- **👥 User Management** - Create/manage officers and departments
- **📊 System Analytics** - Comprehensive dashboards and reports
- **🔐 Audit Logs** - Immutable, hash-chained activity records
- **⚙️ Full Control** - Manage all complaints and assignments

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         INTERNET                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  Nginx (SSL/TLS, Static Files, Reverse Proxy)               │
│  • Port 443/80                                              │
│  • Let's Encrypt SSL                                        │
│  • Security Headers                                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  Gunicorn (WSGI Server)                                     │
│  • 4 Workers                                                │
│  • Port 8000                                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  Flask Application                                          │
│  • Blueprints (public, auth, officer, admin)                │
│  • CSRF Protection                                          │
│  • Session Management                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────┐      ┌───────────▼────────┐
│   MySQL 8.0    │      │   Redis (Celery)   │
│   • Complaints │      │   • Async Tasks    │
│   • Users      │      │   • Notifications  │
│   • Audit Logs │      │                    │
└────────────────┘      └────────────────────┘
```

## 🚀 Quick Start

### Local Development

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/mibsp.git
cd mibsp

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env with your settings

# 5. Initialize database
flask db upgrade
python seed.py

# 6. Run the application
flask run
```

Visit `http://localhost:5000` in your browser.

### Default Credentials

| Role     | Username      | Password     |
|----------|---------------|--------------|
| Admin    | admin         | Admin@1234   |
| Officer  | officer_water | Officer@1234 |

**⚠️ Change these immediately after first login!**

## 🖥️ VPS Deployment (Production)

### Requirements
- Ubuntu 22.04 LTS
- 2GB RAM minimum (4GB recommended)
- 40GB SSD storage
- Domain name pointed to server

### One-Command Deployment

```bash
# Download and run the deployment script
curl -fsSL https://raw.githubusercontent.com/yourusername/mibsp/main/deploy/vps_setup.sh | sudo bash
```

Or manually:

```bash
# 1. Set environment variables
export DOMAIN=yourdomain.com
export DB_PASSWORD=your_secure_password

# 2. Run the setup script
sudo bash deploy/vps_setup.sh
```

### Manual VPS Setup

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install -y python3-pip nginx mysql-server redis-server git

# 3. Setup MySQL
sudo mysql -e "CREATE DATABASE mibsp;"
sudo mysql -e "CREATE USER 'mibsp_user'@'localhost' IDENTIFIED BY 'password';"
sudo mysql -e "GRANT ALL PRIVILEGES ON mibsp.* TO 'mibsp_user'@'localhost';"

# 4. Clone and setup app
cd /var/www
git clone https://github.com/yourusername/mibsp.git
cd mibsp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn pymysql

# 5. Configure environment
cp .env.example .env
# Edit .env with production settings

# 6. Initialize database
flask db upgrade
python seed.py

# 7. Setup Gunicorn service
sudo cp deploy/gunicorn.service /etc/systemd/system/
sudo systemctl enable mibsp
sudo systemctl start mibsp

# 8. Setup Nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/mibsp
sudo ln -sf /etc/nginx/sites-available/mibsp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 9. Setup SSL
sudo certbot --nginx -d yourdomain.com
```

## 🐳 Docker Deployment

```bash
# Using Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f web

# Run migrations
docker-compose exec web flask db upgrade
```

## ☁️ Render.com Deployment

1. Fork this repository
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Render will automatically detect `render.yaml` and deploy

Or use the Deploy button:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## 📁 Project Structure

```
mibsp/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models/                  # SQLAlchemy models
│   │   └── __init__.py
│   ├── routes/                  # Blueprint routes
│   │   ├── public.py            # Citizen routes
│   │   ├── auth.py              # Authentication
│   │   ├── officer.py           # Officer dashboard
│   │   └── admin.py             # Admin panel
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html
│   │   ├── public/
│   │   ├── auth/
│   │   ├── officer/
│   │   └── admin/
│   ├── static/                  # CSS, JS, uploads
│   │   ├── css/
│   │   ├── js/
│   │   └── uploads/
│   └── utils/                   # Helper functions
│       └── __init__.py
├── deploy/                      # Deployment files
│   ├── vps_setup.sh
│   ├── gunicorn.service
│   ├── nginx.conf
│   ├── celery_supervisor.conf
│   └── backup.sh
├── tests/                       # Test suite
├── config.py                    # Configuration classes
├── wsgi.py                      # WSGI entry point
├── seed.py                      # Demo data
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── requirements.txt
```

## 🔐 Security Features

| Feature | Implementation |
|---------|---------------|
| Password Hashing | PBKDF2-SHA256 via Werkzeug |
| SQL Injection Prevention | SQLAlchemy ORM (no raw SQL) |
| CSRF Protection | Flask-WTF on all POST forms |
| File Upload Security | Whitelist + UUID prefix |
| Session Security | 8-hour timeout, secure cookies |
| Audit Logging | Hash-chained, append-only |
| XSS Protection | Template auto-escaping |
| Rate Limiting | Configurable via Nginx |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_public.py
```

## 📊 Database Schema

### Tables

- **departments** - Government departments/wards
- **services** - Services offered by departments
- **users** - Officers and administrators
- **complaints** - Anonymous citizen complaints
- **audit_logs** - Immutable activity records

### Relationships

```
Department 1---* Service
Department 1---* User
Department 1---* Complaint
Service 1---* Complaint
User 1---* Complaint (assigned_to)
User 1---* AuditLog
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment (development/production) | development |
| `SECRET_KEY` | Flask secret key | (generate) |
| `MYSQL_HOST` | MySQL server host | localhost |
| `MYSQL_USER` | MySQL username | mibsp_user |
| `MYSQL_PASSWORD` | MySQL password | (required) |
| `MYSQL_DB` | MySQL database name | mibsp |
| `DATABASE_URL` | PostgreSQL URL (Render) | (optional) |
| `UPLOAD_FOLDER` | File upload directory | uploads |
| `MAX_CONTENT_LENGTH` | Max upload size (bytes) | 16777216 |
| `REDIS_URL` | Redis connection URL | redis://localhost:6379/0 |
| `SESSION_LIFETIME_HOURS` | Session timeout | 8 |

## 📝 API Endpoints

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Homepage |
| `/submit` | GET/POST | Submit complaint |
| `/track` | GET/POST | Track complaint |
| `/dashboard` | GET | Public statistics |
| `/api/stats` | GET | Get statistics JSON |
| `/api/chart/monthly` | GET | Monthly chart data |
| `/api/chart/dept` | GET | Department chart data |
| `/api/chart/status` | GET | Status breakdown |
| `/api/services/<id>` | GET | Get services for department |
| `/health` | GET | Health check |

### Protected Endpoints

| Endpoint | Access | Description |
|----------|--------|-------------|
| `/auth/login` | Public | Staff login |
| `/officer/dashboard` | Officer | Officer dashboard |
| `/officer/complaint/<id>` | Officer | View complaint |
| `/admin/dashboard` | Admin | Admin dashboard |
| `/admin/complaints` | Admin | All complaints |
| `/admin/officers` | Admin | Manage officers |
| `/admin/departments` | Admin | Manage departments |
| `/admin/audit-logs` | Admin | View audit logs |

## 🛠️ Troubleshooting

### MySQL Connection Issues

```bash
# Check MySQL status
sudo systemctl status mysql

# Test connection
mysql -u mibsp_user -p -e "SELECT 1"

# Check logs
sudo tail -f /var/log/mysql/error.log
```

### Nginx 502 Error

```bash
# Check Gunicorn status
sudo systemctl status mibsp

# Check Gunicorn logs
sudo tail -f /var/log/mibsp/error.log

# Restart services
sudo systemctl restart mibsp
sudo systemctl restart nginx
```

### File Upload Errors

```bash
# Check upload directory permissions
ls -la /var/www/mibsp/uploads

# Fix permissions
sudo chown -R www-data:www-data /var/www/mibsp/uploads
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Bootstrap](https://getbootstrap.com/) - UI framework
- [Chart.js](https://www.chartjs.org/) - Charts and visualizations
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM

## 📞 Support

For support, email support@mibsp.gov.in or open an issue on GitHub.

---

**Made with ❤️ for transparent governance**
