# First-Time Developer Setup Guide

Welcome to AegisAIS! This guide walks you through setting up your development environment for the first time. Estimated time: **15–30 minutes**.

---

## Prerequisites

Before starting, ensure you have:

- **macOS/Linux/WSL2**: Unix-like terminal
- **Git**: `git --version` (should be 2.30+)
- **Docker Desktop**: `docker --version` (should be 20.10+)
- **Node.js**: `node --version` (should be 18+ LTS; use `nvm` to manage versions)
- **Python**: `python3 --version` (should be 3.11+)
- **Turbo**: `npm install -g turbo`

### Quick Install (macOS with Homebrew)

```bash
brew install git docker node python@3.11 nvm
nvm install 18
nvm use 18  # Make default
npm install -g turbo
```

---

## Step 1: Clone and Install Dependencies

```bash
# Clone repository
git clone https://github.com/giselleevita/aegisais.git
cd aegisais

# Install root dependencies (turborepo setup)
npm install

# Install Python virtual environment (for API)
cd apps/api
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.lock
cd ../..
```

### Verify Installation

```bash
python3 -m venv --version  # Should show version
node --version              # Should show v18+
turbo --version             # Should show recent version
```

---

## Step 2: Environment Configuration

### Backend (API) Configuration

```bash
cd apps/api

# Copy demo environment file
cp .env.example .env

# Verify these values are set (demo values are fine for dev):
# AISSTREAM_API_KEY=sk-demo-key
# OPENSKY_USERNAME=demo
# OPENSKY_PASSWORD=demo
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/aegisais_dev
# REDIS_URL=redis://localhost:6379
# JWT_SECRET=dev-secret-key-not-for-production
```

### Frontend (Web) Configuration

```bash
cd apps/web

# Copy example environment
cp .env.example .env.local

# Verify these values:
# VITE_API_BASE_URL=http://localhost:8001
# VITE_USE_LEGACY_UI=false  # Modern UI by default
```

---

## Step 3: Start Docker Services

Before running the app, start supporting services (PostgreSQL, Redis, MQTT):

```bash
cd aegisais  # Back to root

# Start all services (includes API, web, BFF, databases)
docker-compose -f infra/docker/docker-compose.yml up -d

# Verify services are running
docker ps | grep aegisais

# Expected containers:
# - postgres:15 (database)
# - redis:7 (caching)
# - emqx/emqx:latest (MQTT broker for IoT)
# - nginx (local reverse proxy)
```

### Verify Database is Ready

```bash
cd apps/api
source .venv/bin/activate

# Run migrations
alembic upgrade head

# Seed demo data (optional)
python scripts/generate_demo_data.py

echo "✓ Database ready"
```

---

## Step 4: Start Development Servers

### In Terminal 1: API Backend

```bash
cd apps/api
source .venv/bin/activate

# Start API server on port 8001
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Expected output:**

```
INFO:     Uvicorn running on http://0.0.0.0:8001
Press CTRL+C to quit
```

### In Terminal 2: BFF Gateway (optional, for full stack)

```bash
cd apps/bff
npm run dev

# Starts on port 3001
# Listens on http://localhost:3001
```

### In Terminal 3: Web Frontend

```bash
cd apps/web
npm run dev

# Starts on port 5173 (Vite dev server)
# Visit http://localhost:5173 in browser
```

---

## Step 5: Verify Everything Works

### API Health Check

```bash
curl http://localhost:8001/health
# Expected: {"status": "healthy"}
```

### Web UI Health Check

Open browser: http://localhost:5173

- Should see map view (or legacy UI if `VITE_USE_LEGACY_UI=true`)
- Should connect to WebSocket (icon shows connected status in top right)

### Database Check

```bash
cd apps/api
source .venv/bin/activate
python -c "from app.core.database import engine; print('✓ DB connected')"
```

---

## Step 6: Run Tests

### Backend Tests

```bash
cd apps/api
source .venv/bin/activate
pytest tests/ -v
```

### Frontend Tests

```bash
cd apps/web
npm run test
```

### All Tests at Once

```bash
turbo run test  # From root
```

---

## Step 7: Understand Directory Structure

**Key folders to know:**

| Path                     | Purpose                                                 |
| ------------------------ | ------------------------------------------------------- |
| `apps/api/app/modules/`  | Feature modules (alerts, vessels, IoT, sanctions, etc.) |
| `apps/api/app/core/`     | Core infrastructure (database, config, security)        |
| `apps/api/tests/`        | API tests                                               |
| `apps/web/src/`          | React frontend source                                   |
| `apps/web/src/features/` | Feature components (map, vessels, alerts)               |
| `apps/bff/src/`          | Fastify backend-for-frontend gateway                    |
| `docs/`                  | Documentation organized by domain                       |
| `infra/docker/`          | Docker Compose and nginx config                         |
| `infra/k8s/`             | Kubernetes manifests for production                     |

---

## Step 8: Common Development Workflows

### Adding a New Feature

1. **Create module structure** (if it's a new domain)

   ```bash
   cd apps/api/app/modules
   mkdir my_feature
   touch my_feature/{__init__.py,models.py,schemas.py,router.py,service.py}
   ```

2. **Write tests first**

   ```bash
   cd apps/api/tests
   touch test_my_feature.py

   # Write test:
   def test_my_feature_endpoint():
       response = client.get("/api/my-feature")
       assert response.status_code == 200
   ```

3. **Implement feature**

   ```bash
   cd apps/api/app/modules/my_feature
   # Edit router.py with your endpoint
   # Edit models.py with your database schema
   # Edit service.py with business logic
   ```

4. **Run tests**

   ```bash
   pytest tests/test_my_feature.py -v
   ```

5. **Frontend integration** (if UI is needed)
   ```typescript
   // apps/web/src/features/myFeature/hooks/useMyFeature.ts
   export function useMyFeature() {
     const [data, setData] = useState(null);
     useEffect(() => {
       fetch("http://localhost:8001/api/my-feature")
         .then((r) => r.json())
         .then(setData);
     }, []);
     return data;
   }
   ```

### Running a Specific Test

```bash
cd apps/api
source .venv/bin/activate
pytest tests/test_assets_iot_api.py::test_register_device -v
```

### Checking Code Quality

```bash
cd apps/api
ruff check .          # Linting
mypy app/             # Type checking
black --check app/    # Code formatting
```

### Database Schema Changes

```bash
cd apps/api

# Generate migration from model changes
alembic revision --autogenerate -m "description of change"

# Review migration in alembic/versions/
# Then apply:
alembic upgrade head

# Verify with:
alembic current
alembic history
```

---

## Step 9: Debugging

### Python Debugging in VSCode

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8001"],
      "jinja": true,
      "cwd": "${workspaceFolder}/apps/api"
    }
  ]
}
```

### Check Logs

```bash
# API logs
docker logs aegisais-api 2>&1 | tail -50

# Web dev server
npm run dev 2>&1 | grep -i error

# Database logs
docker logs aegisais-postgres 2>&1 | tail -20
```

### Reset Database

```bash
cd apps/api
source .venv/bin/activate

# Option 1: Drop everything and restart
alembic downgrade base
alembic upgrade head
python scripts/generate_demo_data.py

# Option 2: Full Docker reset
docker-compose -f infra/docker/docker-compose.yml down -v  # -v removes volumes
docker-compose -f infra/docker/docker-compose.yml up -d
alembic upgrade head
```

---

## Step 10: Staying Up to Date

### Daily Development

```bash
# Pull latest changes
git pull origin main

# Install new dependencies if package.json changed
npm install
pip install -r apps/api/requirements-dev.lock

# Restart services
docker-compose -f infra/docker/docker-compose.yml down
docker-compose -f infra/docker/docker-compose.yml up -d
```

### Reading Documentation

- **Start here**: `docs/README.md` (navigate all domains)
- **For your feature**: Check `docs/product/`, `docs/architecture/`
- **For operations**: Check `docs/operations/`
- **For deployment**: Check `docs/security/`

---

## Troubleshooting

| Problem                                      | Solution                                                                         |
| -------------------------------------------- | -------------------------------------------------------------------------------- |
| "Port 8001 already in use"                   | `lsof -i :8001` to find process, then `kill -9 PID`                              |
| "ModuleNotFoundError: No module named 'app'" | Ensure you're in `apps/api/` and venv is activated (`source .venv/bin/activate`) |
| "CORS error in browser"                      | Check `VITE_API_BASE_URL` matches your API server URL                            |
| "Cannot connect to PostgreSQL"               | Verify Docker container is running: `docker ps \| grep postgres`                 |
| "Redis connection refused"                   | Restart Redis: `docker restart aegisais-redis`                                   |
| "Node version mismatch"                      | Use `nvm use 18` or install via `nvm install 18`                                 |
| "Alembic migration conflicts"                | See `docs/operations/DB_MIGRATION_SETUP.md` for recovery                         |

---

## Next Steps

1. **Pick a feature** from [docs/product/FEATURES_IMPLEMENTED.md](../product/FEATURES_IMPLEMENTED.md)
2. **Read the backlog** at [docs/governance/BUSINESS_LOGIC_IMPLEMENTATION_BACKLOG.md](../governance/BUSINESS_LOGIC_IMPLEMENTATION_BACKLOG.md)
3. **Open an issue** on GitHub and start coding!
4. **Ask questions** in the `#engineering` Slack channel

Welcome aboard! 🚀
