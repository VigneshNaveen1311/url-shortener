# URL Shortener + Redis Cache + PostgreSQL + Custom Load Balancer

## Important Commands
Run these to set up and manage the project:
```
docker compose up --build
docker compose down
docker compose logs -f
docker ps
psql -U postgres -h localhost
```

## Prerequisites
Ensure you have the following installed before running the project:

- Docker Desktop (includes Docker Engine + Docker Compose)
- Git (optional, for cloning the repository)

### Optional (for local development / debugging)

These are **not required** when using Docker Compose, but may be useful:

- Python 3.10+
- `pip`
- PostgreSQL client (`psql`) for manually inspecting the database

A URL Shortener built with FastAPI, PostgreSQL, Redis, and a custom Python reverse proxy/load balancer.

Update the Prerequisites list to include inline footnote references and place footnote definitions below.

For clarity, the optional items now reference the explanatory footnotes below:

- Python 3.10+
- `pip`
- PostgreSQL client (`psql`)

Redis — used for caching and backend health state. You can run the included `redis` service via Docker Compose or install Redis locally.

Python — Python 3.10+ is required to run the backend directly; install dependencies with `pip install -r requirements.txt` or via the provided `pyproject.toml`.

PostgreSQL — the app stores data in Postgres. Use the `postgres` service in Docker Compose or connect with a local Postgres instance using `psql`.

This project was built incrementally while learning:

- FastAPI
- PostgreSQL
- Redis
- Reverse Proxies
- Load Balancing
- Health Checks
- Caching
- Analytics
- Docker


---

# Architecture

```text
Client
   ↓
Load Balancer (Port 8000)
   ↓
 ┌─────────────┬─────────────┬─────────────┐
 │ Backend 1   │ Backend 2   │ Backend 3   │
 │ Port 8001   │ Port 8002   │ Port 8003   │
 └─────────────┴─────────────┴─────────────┘
            ↓
          Redis
            ↓
       PostgreSQL
```

---

# Features

## URL Shortening

Create shortened URLs:

```json
{
  "url": "youtube.com"
}
```

Response:

```json
{
  "short_code": "abc12",
  "short_url": "http://localhost:8000/abc12"
}
```

---

## Redirects

Visiting:

```text
http://localhost:8000/abc12
```

Redirects to:

```text
https://youtube.com
```

---

## Custom Aliases

Request:

```json
{
  "url": "instagram.com",
  "custom_alias": "insta"
}
```

Result:

```text
http://localhost:8000/insta
```

---

## Alias Conflict Protection

Trying to reuse an existing alias returns:

```http
409 Conflict
```

```json
{
  "detail": "Alias already exists"
}
```

---

## Redis Cache

Cache pattern:

```text
Request
   ↓
Redis
   ↓
Cache Hit?
   ↓
 YES → Redirect

 NO
   ↓
PostgreSQL
   ↓
Store in Redis
   ↓
Redirect
```

TTL:

```python
r.set(short_code, row[0], ex=60)
```

Currently cached for:

```text
60 seconds
```

---

## Analytics

Tracks:

- Click count
- Last accessed timestamp

Every redirect executes:

```sql
UPDATE urls
SET click_count = click_count + 1,
    last_accessed = NOW()
WHERE short_code = %s;
```

---

## Custom Load Balancer

Built from scratch using FastAPI + httpx.

Features:

- Round Robin distribution
- Health checks
- Automatic failover
- Request forwarding
- Response forwarding

Backend health is stored in Redis.

---

# Project Structure

```text
url-shortener/
│
├── main.py          # FastAPI application
├── lb.py            # Custom reverse proxy/load balancer
├── db.py            # PostgreSQL connection helper
├── init_db.py       # Database initialization script
├── Dockerfile       # Backend container image
├── Dockerfile.lb    # Load balancer container image
├── docker-compose.yml # Multi-container orchestration
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

# Docker Upgrades

This project now includes a full Docker-based deployment for the complete stack:

- `postgres` service running PostgreSQL
- `redis` service running Redis
- `backend1`, `backend2`, `backend3` services running the FastAPI backend in parallel
- `loadbalancer` service running the custom FastAPI reverse proxy

The Docker Compose setup includes:

- shared PostgreSQL database with persistent volume
- shared Redis cache for both backend and load balancer health state
- three backend replicas with separate server names
- a separate load balancer container exposing HTTP traffic on port `8000`

Run the full system with:

```powershell
docker compose up --build
```

And stop it with:

```powershell
docker compose down
```

---

# Database Setup

## Login

```powershell
psql -U postgres
```

---

## List Databases

```sql
\l
```

---

## Connect to Project Database

```sql
\c url_shortener
```

---

## List Tables

```sql
\d
```

---

## View URLs

```sql
SELECT * FROM urls;
```

---

## Create Database

```sql
CREATE DATABASE url_shortener;
```

---

## Create Table

```sql
CREATE TABLE urls(
    id SERIAL PRIMARY KEY,
    short_code VARCHAR(10) UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Add Analytics Columns

```sql
ALTER TABLE urls
ADD COLUMN click_count INTEGER DEFAULT 0,
ADD COLUMN last_accessed TIMESTAMP DEFAULT NOW();
```

---

## Common PostgreSQL Mistake

If you see:

```sql
ERROR: relation "urls" does not exist
```

You're probably connected to the wrong database.

Check:

```sql
SELECT current_database();
```

Or reconnect:

```sql
\c url_shortener
```

---

# Redis Setup

Run Redis in Docker:

```powershell
docker run -p 6379:6379 redis
```

If Docker Desktop is not running:

1. Open Docker Desktop
2. Start the Redis container
3. Verify port 6379 is exposed

---

## Quick Redis Test

```python
import redis

r = redis.Redis(
    host="localhost",
    port=6379,
    db=0
)

r.set("foo", "bar")
print(r.get("foo"))
```

Output:

```text
b'bar'
```

---

# Running the Application

## Backend Server 1

```powershell
$env:SERVER="Server1"
uvicorn main:app --reload --port 8001
```

---

## Backend Server 2

```powershell
$env:SERVER="Server2"
uvicorn main:app --reload --port 8002
```

---

## Backend Server 3

```powershell
$env:SERVER="Server3"
uvicorn main:app --reload --port 8003
```

---

## Load Balancer

```powershell
uvicorn lb:app --reload --port 8000
```

---

# Testing

## Check Backend Health

Server 1:

```text
http://localhost:8001/health
```

Server 2:

```text
http://localhost:8002/health
```

Server 3:

```text
http://localhost:8003/health
```

Expected response:

```json
{
  "status": "ok",
  "server": "Server1"
}
```

---

## Create Short URL (PowerShell)

```powershell
Invoke-RestMethod `
-Uri "http://localhost:8000/shorten" `
-Method POST `
-ContentType "application/json" `
-Body '{"url":"youtube.com"}'
```

Example output:

```text
short_code short_url
---------- ---------
N3EBf      http://localhost:8000/N3EBf
```

---

## Create Custom Alias

```powershell
Invoke-RestMethod `
-Uri "http://localhost:8000/shorten" `
-Method POST `
-ContentType "application/json" `
-Body '{"url":"instagram.com","custom_alias":"insta"}'
```

---

## Browser Redirect Test

Visit:

```text
http://localhost:8000/insta
```

Expected:

```text
https://instagram.com
```

---

## curl.exe (Windows)

PowerShell aliases `curl` to `Invoke-WebRequest`.

Use:

```powershell
curl.exe -X POST "http://localhost:8000/shorten" `
-H "Content-Type: application/json" `
-d "{\"url\":\"youtube.com\"}"
```

---

# Known Limitations

## Swagger UI Through Load Balancer

GET redirects work through the load balancer.

POST requests are easier to test using:

```powershell
Invoke-RestMethod
```

instead of Swagger UI.

---

## In-Memory Round Robin State

The load balancer currently uses:

```python
itertools.cycle()
```

If the load balancer restarts, the rotation order resets.

---

## No Authentication

Currently anyone can:

- Create URLs
- Create aliases
- Access redirects

---

## No Rate Limiting

Potential abuse is not prevented.

Examples:

```text
Millions of URL creations
Millions of redirect requests
```

---

## Single PostgreSQL Instance

All backend servers share the same PostgreSQL database.

No database replication has been implemented.

---

# Future Improvements

- Docker Compose
- SQLAlchemy
- JWT Authentication
- Rate Limiting
- User Accounts
- URL Expiry
- Analytics API
- Country/IP Tracking
- Admin Dashboard
- Deployment to VPS
- Nginx Reverse Proxy
- Kubernetes
- PostgreSQL Replication

---

# What I Learned

## FastAPI

- GET
- POST
- Path parameters
- Request bodies
- Pydantic models
- RedirectResponse
- HTTPException

## PostgreSQL

- CREATE TABLE
- INSERT
- SELECT
- UPDATE
- ALTER TABLE
- Constraints
- ON CONFLICT
- Transactions

## Redis

- Cache
- TTL
- Key-value storage
- Cache-aside pattern

## Distributed Systems

- Reverse Proxy
- Load Balancing
- Health Checks
- Failover
- Multiple Backend Instances

## Architecture

Built a miniature production-style system:

```text
Load Balancer
      ↓
FastAPI Servers
      ↓
Redis Cache
      ↓
PostgreSQL
```

---

# Notes

This project was built primarily as a backend learning exercise to understand how different components in a production system interact:

- FastAPI for APIs
- PostgreSQL for persistence
- Redis for caching and health tracking
- A custom Python reverse proxy/load balancer
- Multiple backend instances sharing the same database and cache

The goal was to learn the concepts by implementing them manually before using production tools such as Nginx, HAProxy, Kubernetes, or managed cloud services.