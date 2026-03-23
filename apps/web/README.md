# AegisAIS Frontend

## Prerequisites

- Node.js 20.19.0 or higher (22.12+ also works)
- npm 10.8.2 or higher

## Setup

1. **Ensure you're using the correct Node version:**

   If you have nvm installed:
   ```bash
   nvm use
   # or explicitly:
   nvm use 20.19.0
   ```

   If you don't have nvm, make sure Node.js 20.19+ is installed and active.

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

   The app will be available at `http://127.0.0.1:5174` (see `vite.config.ts`).

4. **Build for production:**
   ```bash
   npm run build
   ```

## Troubleshooting

### "Vite requires Node.js version 20.19+"

If you see this error, you're not using the correct Node version:

1. **Check your current Node version:**
   ```bash
   node --version
   ```

2. **If it's not 20.19.0 or higher, activate nvm and use the correct version:**
   ```bash
   source ~/.zshrc  # or restart your terminal
   nvm use 20.19.0
   ```

3. **Verify:**
   ```bash
   node --version  # Should show v20.19.0
   ```

4. **Then try again:**
   ```bash
   npm run dev
   ```

## Environment Variables

Create a `.env` file in the frontend directory to configure the API URL:

```
VITE_API_BASE_URL=http://localhost:8001
```

### UI mode

By default the app loads the **AML analyst console** (triage split view, investigation, globe, etc.). Upload and replay live under **Triage** → “Data upload & replay”. The root path **`/`** redirects to **`/triage`** (alert queue + map). Legacy **`/lab`** redirects to **`/triage`**.

The API exposes optional **integration feed status** for the Admin screen:

- `GET /v1/integrations/feeds` (authenticated: viewer role or above) — returns S-AIS / SAR / RF rows derived from server config (no secrets in the JSON).

To use the **legacy tabbed UI** (original Home / Dashboard / … tabs and sidebar replay), set:

```
VITE_USE_LEGACY_UI=true
```

Users can also switch modes from the app: **Classic tabbed UI** in the analyst footer, or **Analyst console** in the legacy header (preference is stored in `localStorage`).

## End-to-end tests

Playwright starts the Vite dev server on port **5174** by default. If that port is already taken by a stale process, tests can fail with an empty page. Either free the port or run against a preview build:

```bash
npm run build
npx vite preview --host 127.0.0.1 --port 4173
BASE_URL=http://127.0.0.1:4173 npm run test:e2e
```
