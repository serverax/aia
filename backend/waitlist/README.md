# AiA Waitlist API

Simple Flask API for managing waitlist signups.

## Quick Start

### Local Development
```bash
pip install -r requirements.txt
python app.py
# API runs at http://localhost:5000
```

### Docker
```bash
docker-compose up
# API at http://localhost:5000
```

### Kubernetes
```bash
docker build -t aia-waitlist:latest .
kubectl apply -f k8s.yaml
```

## API Endpoints

### Join Waitlist
```bash
POST /api/waitlist/join
{
  "name": "John Doe",
  "email": "john@company.com",
  "profession": "Engineer",
  "company": "ACME Corp"
}
```

### Get Count
```bash
GET /api/waitlist/count
```

### List All (Admin)
```bash
GET /api/waitlist/list
Headers: X-API-Key: admin-key-change
```

### Health
```bash
GET /health
```

## Admin Commands
```bash
python admin.py list
```

## Database
SQLite: `waitlist.db`

Table: `waitlist` (id, name, email, profession, company, created_at)

## Environment
- FLASK_ENV=development (local)
- FLASK_ENV=production (K8s)

## Security Checklist
- [ ] Change admin API key
- [ ] Configure HTTPS (Let's Encrypt)
- [ ] Add rate limiting
- [ ] Enable CORS properly
- [ ] Backup database regularly
