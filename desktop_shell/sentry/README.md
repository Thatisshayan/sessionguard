# Sentry Crash Reporting

SessionGuard uses Sentry for frontend (React) and desktop (Tauri/Rust) crash reporting.

## Setup

### 1. Create a Sentry project

Go to https://sentry.io and create a new project:
- For frontend: choose "React" 
- For Tauri: choose "Rust"

### 2. Set DSN environment variables

**Frontend** — create `frontend/.env.local`:
```
VITE_SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
VITE_APP_VERSION=1.0.0
```

**Tauri** — set environment variable when running:
```bash
set SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
cargo tauri build
```

Or add to your CI/CD secrets for builds.

### 3. Test it

Start the app and verify in Sentry that test events appear.

## What gets captured

**Frontend:**
- Unhandled JavaScript exceptions
- API request failures
- Performance traces
- User sessions (with PII redacted)

**Desktop (Rust):**
- Panics and crashes
- Unhandled errors at the Rust boundary