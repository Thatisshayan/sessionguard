# How To Use SessionGuard

This guide is for a local user running SessionGuard on their own machine.

It covers:
- first-time setup
- starting the app
- creating an account and signing in
- the main day-to-day workflows
- where to go for admin and advanced features

It does not cover:
- GitHub release engineering
- contributor workflow
- production deployment

## What SessionGuard Is

SessionGuard is a local-first session intelligence app for reviewing casino or slot-session data.

You can use it to:
- import session data from CSV files
- review sessions and metrics
- inspect OCR and video-derived events
- monitor live activity
- generate exports and evidence packages
- manage settings, backups, and admin functions

## Before You Start

Recommended local prerequisites:
- Python installed and available on `PATH`
- Node.js installed and available on `PATH`
- FFmpeg installed for video workflows
- Tesseract installed for OCR workflows

If FFmpeg or Tesseract are missing, the app can still start, but OCR and video features will be limited.

## Required Local Config

Create a local `.env` file in the repo root before you start the backend.

The quickest path is:

```bat
copy .env.example .env
```

Then edit `.env` and set at least:

```text
SECRET_KEY=<generate-this-locally>
NVIDIA_API_KEY=<paste-your-nvidia-key-here>
```

Notes:
- `SECRET_KEY` is required for normal non-test app startup. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`.
- `NVIDIA_API_KEY` is optional. If unset, SessionGuard falls back to Ollama or rule-based analysis instead of NVIDIA AI.
- Environment variables are the preferred source of truth. The repo still has some legacy config-file fallbacks, but `.env` is the correct user-facing setup path.
- For the installed desktop app, the writable runtime config is more important than the repo-root `.env`. On first launch the app copies `config/app_config.json` into its local data directory and can read `ai.nvidia_api_key` from that runtime copy.

## First-Time Setup

From the repo root, run:

```bat
scripts\setup.bat
```

What this does:
- installs Python dependencies from `requirements.txt`
- installs frontend dependencies in `frontend\`
- installs Tauri desktop dependencies in `desktop_shell\`
- checks for FFmpeg and Tesseract

When setup completes, the script tells you to run `scripts\run_all.bat`.

## Start The Application

From the repo root, run:

```bat
scripts\run_all.bat
```

This launches three pieces:
- backend API at `http://127.0.0.1:8000`
- frontend at `http://localhost:5173`
- Tauri desktop shell from `desktop_shell\`

Important:
- This `run_all.bat` flow is the development workflow. It runs the backend and frontend as separate local processes, then opens the desktop shell against them.
- The installed Tauri desktop app is intended to start its own backend automatically. You should not normally need to run a separate backend for the installed app.
- If the installed app cannot start its bundled backend, it will appear broken even though the dev workflow still works.

If you prefer the browser UI, open:

```text
http://localhost:5173
```

If you want API docs, open:

```text
http://127.0.0.1:8000/docs
```

## Create An Account And Sign In

When the UI opens, go to the login page.

You can:
- sign in with an existing account
- switch to `Create Account`
- create a new local user

After signup, the app logs you in automatically.

Notes:
- some pages are available to normal users
- some pages require `admin`
- the Admin page is route-guarded and will redirect non-admin users away

## Main Navigation

The exact menu may evolve, but the main working areas are:
- Dashboard
- Sessions
- Upload
- Live Monitor
- Compare
- Reports / Exports
- Review Queue
- Profiles
- Settings
- Jobs Monitor
- Admin

## Typical Workflow

## 1. Import Data

Use `Upload` when you want to bring in CSV-based session or spin data.

Typical flow:
1. Open `Upload`
2. Choose the file type the page expects
3. Select your CSV
4. Submit the import
5. Review the result in Sessions or the Review Queue

Use this when:
- you already have structured session exports
- you want metrics, trends, and comparisons quickly

## 2. Review Sessions

Open `Sessions` to browse imported sessions.

From there you can typically:
- inspect a session record
- review OCR/event outputs
- check balances, bets, wins, and summaries
- move into related exports or analysis

Use `Dashboard` for the broad view and `Session Detail` for per-session inspection.

## 3. Compare Sessions

Use `Compare` to place multiple sessions side by side.

This is useful when you want to:
- compare outcomes across days or games
- inspect RTP or loss patterns
- contrast different sessions before exporting results

## 4. Use Live Monitor

Use `Live Monitor` for active or near-real-time tracking.

Depending on your local setup, this can include:
- mock/live development monitoring
- screen-driven event collection
- live coaching or intervention messages

If live capture depends on OCR or screen tooling, make sure Tesseract is installed and working locally.

## 5. Work With OCR And Video

SessionGuard supports OCR and video-related workflows, but they depend on local tooling.

Use these features when you need to:
- extract fields from frames
- inspect OCR output
- process video into events
- review uncertain results in the Review Queue

For best results:
- install Tesseract
- install FFmpeg
- keep source media on a local disk

If these tools are missing, start with CSV import first and come back to OCR/video later.

## 6. Review Queue

Use `Review Queue` when the system is uncertain about imported or extracted data.

This is where you clean up borderline cases before trusting the final analysis.

Use it to:
- inspect low-confidence items
- resolve questionable OCR/event outputs
- improve trust in downstream metrics and exports

## 7. Exports And Evidence

Use the export/reporting surfaces when you want to produce artifacts for your own review or record-keeping.

Depending on the screen and your role, you can work with:
- reports
- downloadable exports
- evidence-related output

Some advanced export/evidence capabilities exist in the backend even if they are not all exposed as full top-level UI pages yet.

## 8. Settings, Backup, And Restore

Use `Settings` for environment-level tasks and useful links.

Useful items:
- links to the frontend and API docs
- database backup
- database restore

Backup and restore are especially important if you are using this locally as your own working app.

Recommended habit:
- back up before major imports
- back up before restore operations
- keep a dated copy of any important `.db` backup outside the repo

## 9. Admin Features

Use `Admin` only if your account has the `admin` role.

Admin functions include things like:
- viewing system health
- viewing stats
- managing users
- checking audit activity
- performing admin-level maintenance

If you are redirected away from Admin, your current account is not an admin account.

## What Is UI-Ready vs API-Only

Most normal local usage is available through the UI.

Some backend capabilities are still better thought of as API-first or partially exposed, including parts of:
- evidence package management
- clustering and dataset-quality surfaces
- some AI compare/review-support endpoints

If you need those immediately, use:
- the API docs at `http://127.0.0.1:8000/docs`
- the typed frontend API layer in `frontend\src\services\api.ts` as the repo source of truth

## NVIDIA AI Setup

If you want NVIDIA-backed AI insights instead of fallback behavior:

1. Create `.env` from `.env.example`
2. Set `NVIDIA_API_KEY=nvapi-...`
3. Restart the backend
4. Open a session detail page and use the AI analysis panel

For the installed desktop app, use one of these instead:
- set a Windows user or machine environment variable named `NVIDIA_API_KEY`
- or edit the runtime `app_config.json` created in the app's writable local data directory and set `ai.nvidia_api_key`

If AI still shows as unavailable:
- confirm the backend was restarted after editing `.env`
- confirm `NVIDIA_API_KEY` is present in the repo-root `.env`
- check `GET /api/v1/ai/status` in `http://127.0.0.1:8000/docs`

## Troubleshooting

## The app does not start

Check:
- `scripts\setup.bat` completed successfully
- Python is on `PATH`
- Node.js is on `PATH`
- each window opened by `scripts\run_all.bat` is still running
- `.env` exists in the repo root
- `SECRET_KEY` is set in `.env`

## The frontend opens but data does not load

Check:
- backend window is still running
- `http://127.0.0.1:8000/health` responds
- `http://127.0.0.1:8000/docs` opens

## OCR or video features do not work

Check:
- Tesseract is installed
- FFmpeg is installed
- the source files are valid and accessible

## Admin page does not open

Check:
- you are signed in
- your account has the `admin` role

## The installed desktop app opens but seems non-functional

Check:
- whether the installed app started its own backend successfully
- whether Python and bundled runtime assets were packaged correctly for that build
- whether the runtime config in the app's local data directory contains `ai.nvidia_api_key` if you are not using an environment variable
- whether `sessionguard.log` exists next to the desktop executable and contains backend startup errors

If you need a reliable local fallback while debugging the packaged app, use the repo dev flow:
- `scripts\run_all.bat`
- then open `http://localhost:5173` or the Tauri dev shell

Current packaged-release scope:
- Windows installers are the supported packaged desktop target right now.
- macOS/Linux packaged releases are deferred until those platforms have their own bundled-runtime path.

## Where To Start If You Just Want To Use It

If you want the shortest path:

1. Run `scripts\setup.bat`
2. Run `scripts\run_all.bat`
3. Open `http://localhost:5173`
4. Create an account
5. Start with `Upload`, `Sessions`, and `Dashboard`
6. Add OCR/video workflows only after Tesseract and FFmpeg are confirmed working

## Related Docs

- [README.md](../README.md)
- [docs/README.md](README.md)
- [Deferred Work Register](governance/DEFERRED_WORK.md)
