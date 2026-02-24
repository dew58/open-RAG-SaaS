# Multi-Tenant RAG SaaS System

Production-grade Retrieval-Augmented Generation platform built with FastAPI, PostgreSQL, ChromaDB, and OpenAI.

---

## Architecture Overview

```
Client (React App) → Nginx (TLS, rate limit) → FastAPI (async) → PostgreSQL
                                                           → ChromaDB (per-tenant collection)
                                                           → Gemini/Ollama (embeddings + chat)
```

### Multi-Tenancy Model
Each client (tenant) gets:
- Isolated database rows via `client_id` foreign keys
- Isolated ChromaDB collection: `client_{uuid}`  
- Isolated file storage directory: `uploads/{client_id}/`
- JWT tokens carry `client_id` — all queries automatically scoped

---

## Project Structure

```
rag-saas/
├── app/                         # Backend (FastAPI)
│   ├── main.py                  # application factory
│   ├── rag_engine/              # ChromaDB + LangChain RAG pipeline
│   └── ...
├── frontend/                    # Frontend (React + Vite + TS)
│   ├── src/
│   │   ├── api/                 # API client layer
│   │   ├── components/          # Shared components
│   │   └── ...
│   ├── package.json
│   └── ...
├── alembic/                     # Database migrations
├── docker/
│   └── nginx.conf               # Production nginx config
├── scripts/
│   └── postgres_init.sql        # DB initialization
├── Dockerfile                   # Multi-stage production build
├── docker-compose.yml           # Full stack orchestration
├── requirements.txt
└── .env.example                 # Backend environment template
```

---

## Frontend Setup (React + TypeScript)

The system includes a modern React frontend built with Vite, TypeScript, and Tailwind CSS.

### Quick Start (Frontend)

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Set up environment
cp .env.example .env
# Default VITE_API_BASE_URL is http://localhost:8000/api/v1 (pointing to backend)

# 4. Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## Quick Start (Backend)

```bash
# 1. Clone and set up environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and secrets

# 2. Start with Docker Compose
docker-compose up -d

# 3. Run migrations
docker-compose run --rm migrate

# 4. Verify health
curl http://localhost/health
```

---

## Production Deployment

### Prerequisites
- Docker 24+ and Docker Compose v2
- TLS certificates (Let's Encrypt via certbot, or your CA)
- Domain pointed to server

### Steps

```bash
# 1. Generate strong secrets
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))"
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"

# 2. Configure environment
cp .env.example .env
# Fill ALL values, especially:
# - SECRET_KEY
# - JWT_SECRET_KEY  
# - POSTGRES_PASSWORD
# - REDIS_PASSWORD
# - OPENAI_API_KEY
# - CORS_ORIGINS

# 3. Place TLS certificates
mkdir -p docker/ssl
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/ssl/
chmod 600 docker/ssl/*.pem

# 4. Deploy
docker-compose up -d

# 5. Run migrations
docker-compose run --rm migrate

# 6. Monitor logs
docker-compose logs -f api
```

---

## API Reference

All endpoints require `Authorization: Bearer <access_token>` except `/auth/register` and `/auth/login`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user + tenant |
| POST | `/api/v1/auth/login` | Login, get tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Current user info |
| GET | `/api/v1/clients/me` | Current tenant info |
| POST | `/api/v1/documents/upload` | Upload document (PDF/DOCX/TXT) |
| GET | `/api/v1/documents` | List documents |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| POST | `/api/v1/chat/query` | Ask a question |
| GET | `/api/v1/chat/history` | Query history |
| GET | `/api/v1/export/queries` | Export logs as Excel |

---

## Database Migrations

```bash
# Generate migration after model changes
alembic revision --autogenerate -m "add_feature_x"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View history
alembic history
```

---

## Security Considerations Checklist

### Authentication & Authorization
- [x] bcrypt password hashing (rounds=12)
- [x] JWT short-lived access tokens (30 min)
- [x] JWT refresh tokens (7 days)
- [x] Account lockout after 5 failed login attempts
- [x] All endpoints require authentication except register/login
- [x] `client_id` embedded in JWT enforces tenant isolation

### Input Validation
- [x] Pydantic schema validation on all inputs
- [x] Password strength enforcement (uppercase, lowercase, digit, special)
- [x] File type validation via magic bytes (not just extension)
- [x] File size limit enforced
- [x] Prompt injection pattern detection
- [x] SQL injection: prevented by SQLAlchemy ORM parameterized queries
- [x] Path traversal: resolved path checked against base directory

### Infrastructure
- [x] Non-root Docker user (UID 1001)
- [x] No hardcoded secrets — all from environment
- [x] TLS termination at nginx
- [x] Security headers (HSTS, CSP, X-Frame-Options)
- [x] Rate limiting at both nginx and FastAPI layers
- [x] CORS strict whitelist

### Data
- [x] Tenant isolation enforced at query level (not just application)
- [x] Soft delete preserves audit trail
- [x] Immutable audit log table
- [x] Chroma collections isolated per client

### What to Add Before Production
- [ ] Secrets manager (AWS Secrets Manager / Vault) instead of .env
- [ ] WAF (AWS WAF, Cloudflare) in front of nginx
- [ ] Database connection via TLS (add `sslmode=require` to DATABASE_URL)
- [ ] Redis TLS (`rediss://`)
- [ ] Log aggregation (Datadog, ELK, CloudWatch)
- [ ] Alerting on error rate spikes
- [ ] API key rotation policy
- [ ] Regular dependency vulnerability scanning (`pip audit`)
- [ ] Penetration testing before launch

---

## Performance Optimization Notes

### Bottlenecks and Mitigations

| Bottleneck | Impact | Mitigation |
|------------|--------|------------|
| OpenAI API latency | 1-5s per query | Caching common queries in Redis; streaming responses |
| ChromaDB sync calls | Blocks event loop | All Chroma calls run via `loop.run_in_executor()` |
| Large file indexing | Memory spike | Background task + batch chunking (50 chunks/batch) |
| DB connection exhaustion | 503 errors | Pool size 20 + overflow 40; NullPool in workers |
| Rate limiter memory | Memory growth | Periodic cleanup of expired entries |
| Concurrent indexing | Collection corruption | Per-client asyncio.Lock |
| Large export queries | Memory spike | 10,000 row cap + streaming response |

### Scaling Strategy

**Vertical scaling** (single server):
- Increase `WORKERS` to `(2 * CPU) + 1`
- Increase `DB_POOL_SIZE` proportionally

**Horizontal scaling** (multiple servers):
- Replace in-memory rate limiter with Redis-backed version (stub provided in `rate_limiter.py`)
- Move ChromaDB to ChromaDB server mode or migrate to Pinecone/Weaviate
- Use S3/GCS for file storage instead of local disk
- Add CDN for exported files

**Async indexing at scale**:
- Replace `asyncio.create_task()` with Celery + Redis broker
- Enables retries, monitoring, and distributed workers

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | - | OpenAI API key |
| `SECRET_KEY` | ✅ | - | App secret (64+ chars) |
| `JWT_SECRET_KEY` | ✅ | - | JWT signing secret (64+ chars) |
| `DATABASE_URL` | ✅ | - | PostgreSQL asyncpg URL |
| `POSTGRES_PASSWORD` | ✅ | - | DB password (docker-compose) |
| `ENVIRONMENT` | ✅ | development | development/staging/production |
| `CORS_ORIGINS` | ✅ | localhost | JSON array of allowed origins |
| `LOG_LEVEL` | ❌ | INFO | DEBUG/INFO/WARNING/ERROR |
| `MAX_FILE_SIZE_MB` | ❌ | 50 | Max upload size |
| `CHUNK_SIZE` | ❌ | 1000 | RAG chunk size in characters |
| `RETRIEVAL_TOP_K` | ❌ | 5 | Chunks retrieved per query |
| `BCRYPT_ROUNDS` | ❌ | 12 | Password hash cost (13-14 for production) |

---

## Troubleshooting

```bash
# View API logs
docker-compose logs -f api

# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d rag_saas

# Check ChromaDB collections
docker-compose exec api python -c "
from app.rag_engine.engine import get_chroma_client
client = get_chroma_client()
print(client.list_collections())
"

# Manual migration
docker-compose run --rm migrate alembic current

# Rebuild after code changes
docker-compose up -d --build api
```
# open-RAG-SaaS
