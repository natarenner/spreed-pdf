# Spreed Automation - Backend PDF & Workflows

This repository contains the backend and automated infrastructure for PDF generation, CRM integration (Ploomes), WhatsApp (BotConversa), and form systems (Formbricks).

## 🚀 Architecture

The solution consists of:
- **FastAPI**: Main API serving the backend and checkout/payment pages.
- **Worker (Dramatiq)**: Asynchronous processing for heavy PDF generation and third-party integrations.
- **PostgreSQL + pgvector**: Relational database with vector support (shared with Formbricks).
- **Redis**: Message broker for Dramatiq task queues.
- **Formbricks**: Survey and form management tool.
- **Nginx (Host)**: Reverse proxy running directly on the Linux host to manage subdomains and SSL.

## 🛠️ Prerequisites

- Docker & Docker Compose
- Nginx installed on the host system
- Certbot (for SSL/HTTPS)

## 📦 Setup & Installation

### 1. Environment Variables
Create a `.env` file based on the example:
```bash
cp example.env .env
```
Fill in the keys for OpenAI, Ploomes, Woovi, BotConversa, and Google Drive.

### 2. Start Infrastructure (Docker)
Start all containers (API, Worker, DB, Redis, Formbricks):
```bash
docker-compose up -d --build
```
*The `scripts/init-db.sh` script will automatically create the `pdf_api` and `formbricks` databases on the first run.*

### 3. Configure Nginx (Host Linux)
Create a new Nginx configuration file at `/etc/nginx/sites-available/spreed-automacao`:

```nginx
# API Subdomain
server {
    listen 80;
    server_name api.spreed-automacao.com.br;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Checkout/Payment (Static Pages)
server {
    listen 80;
    server_name seguro.spreed-automacao.com.br;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Formbricks
server {
    listen 80;
    server_name forms.spreed-automacao.com.br;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the configuration and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/spreed-automacao /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Enable HTTPS (SSL)
Use Certbot to generate certificates for the 3 subdomains:
```bash
sudo certbot --nginx -d api.spreed-automacao.com.br -d seguro.spreed-automacao.com.br -d forms.spreed-automacao.com.br
```

## 🌐 Subdomains

- `api.spreed-automacao.com.br`: API endpoints and Swagger documentation (`/docs`).
- `seguro.spreed-automacao.com.br`: Landing pages for checkout and payment confirmation.
- `forms.spreed-automacao.com.br`: Formbricks dashboard and integrations.

## 📁 Project Structure

- `/api`: FastAPI application source code.
- `/workers`: Asynchronous tasks and integration services (Ploomes, BotConversa, GDrive).
- `/templates`: HTML/JS templates for checkout and payment.
- `/scripts`: Initialization scripts and utilities.
- `/migrations`: Database migration history (Alembic).

## 📄 License

Private and exclusive use - Spreed Automação.
