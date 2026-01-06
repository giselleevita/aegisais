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

   The app will be available at `http://localhost:5173` (or the port Vite assigns).

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
VITE_API_BASE_URL=http://localhost:8000
```
