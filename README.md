# OPERATION HATA
### Hidden Attachment Threat Analyzer

Operation HATA is an AI-assisted cybersecurity platform that automatically monitors
an email account for image attachments, isolates them in a secure quarantine,
runs them through a multi-layer forensic analysis pipeline, computes a transparent
risk score, and asks an AI model to interpret the evidence into a plain-language
security report. It also ships a Manual Scan mode so any image can be analyzed
independently, through the exact same pipeline.

This is a real, working full-stack application — not a static mockup. Every
button performs a real action against a real FastAPI backend with a real
SQLite/PostgreSQL database.

---

## 1. Architecture

```
                         ┌────────────────────────┐
                         │        Frontend         │
                         │  React + Vite + Tailwind │
                         │  (SOC-style dashboard)   │
                         └───────────┬──────────────┘
                                     │ REST + WebSocket
                         ┌───────────▼──────────────┐
                         │        FastAPI            │
                         │  (app/api/*.py routers)   │
                         └───────────┬──────────────┘
                                     │
              ┌──────────────────────┼───────────────────────┐
              │                      │                        │
    ┌─────────▼─────────┐  ┌─────────▼─────────┐   ┌──────────▼─────────┐
    │  Email Monitor      │  │ Scan Orchestrator │   │   PostgreSQL/       │
    │  (IMAP polling loop) │  │ (pipeline runner) │   │   SQLite (SQLAlchemy)│
    └─────────┬─────────┘  └─────────┬─────────┘   └─────────────────────┘
              │                      │
              │            ┌─────────▼──────────────────────────────┐
              │            │   Analysis Modules (app/services/*)     │
              │            │  signature → hash → metadata → entropy  │
              │            │  → steganography → embedded/appended    │
              │            │  → YARA → OCR → QR → URL → risk_engine  │
              │            │  → ai_analyzer → report_generator (PDF) │
              │            └──────────────────────────────────────────┘
              │
    ┌─────────▼─────────┐
    │  Quarantine Dir     │   Attachments are NEVER executed; they are
    │  backend/quarantine │   isolated in per-scan directories with
    │  /<scan_id>/         │   randomly generated filenames.
    └────────────────────┘
```

### Workflow (automatic mode)

```
Email arrives → Monitor detects new message (IMAP, deduped by Message-ID)
→ Image attachment found → downloaded into quarantine/<scan_id>/
→ Scan record created → pipeline runs stage by stage, broadcasting progress
  over WebSocket → risk score computed → AI interprets evidence
→ Dashboard updates in real time → notification shown if risk ≥ MEDIUM
→ PDF report available for download
```

### Workflow (manual mode)

```
User drops/selects an image on the Manual Scan page
→ POST /api/scans/upload validates magic bytes, size, extension
→ POST /api/scans/{id}/start runs the identical pipeline
→ Live timeline shows each stage completing via WebSocket
→ Redirects to the full Scan Result page with all findings + AI report
```

---

## 2. Features

- **Automatic email monitoring** (Gmail via secure IMAP app-password, OAuth2-ready architecture)
- **Manual drag-and-drop scanning** through the identical pipeline
- **Real magic-byte file-type verification** — extension is never trusted
- **MD5 / SHA-1 / SHA-256 hashing**, with optional VirusTotal reputation lookup
- **EXIF/metadata analysis** with anomaly detection (camera, GPS, software, conflicting timestamps)
- **Shannon entropy analysis** (overall + chunked, charted)
- **Steganography heuristics** (LSB ratio + chi-square pair test)
- **Appended-data / embedded-file detection** (ZIP, PE, ELF, PHP, scripts, polyglots)
- **Real YARA scanning** (yara-python) against a modular rule directory
- **OCR** (Tesseract) with social-engineering phrase detection
- **QR code decoding** (pyzbar) with content classification — codes are never auto-visited
- **URL heuristic analysis** (IP hosts, punycode, suspicious TLDs, excessive subdomains, etc.)
- **Transparent, configurable 0–100 risk-scoring engine** with documented, capped weights
- **AI interpretation layer** (Claude) that explains evidence in plain language — with a
  fully-functional deterministic fallback report when no AI key is configured
- **Branded PDF report generation** (ReportLab) covering all 18 report sections
- **Dynamic risk-reactive SOC dashboard** (dark theme, glassmorphism, live WebSocket updates)
- **Quarantine management** with confirmation-gated restore/delete
- **Demo mode** — seeds realistic, clearly-labeled synthetic scans across all 5 risk bands
- **Graceful degradation everywhere** — a missing tool/API key never crashes a scan

---

## 3. Technology Stack

**Frontend:** React 18, Vite, Tailwind CSS, React Router, Axios, Recharts, Lucide Icons, Framer Motion
**Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic, SQLAlchemy, WebSockets
**Database:** SQLite (default, zero-config) or PostgreSQL (set `DATABASE_URL`)
**Security/Analysis tooling:** Pillow, yara-python, pytesseract, pyzbar, OpenCV, ReportLab, cryptography (Fernet)
**AI:** Anthropic Claude API (configurable model/provider)

---

## 4. Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional but recommended for full functionality) YARA, Tesseract OCR, zbar

#### Installing optional external tools

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install -y yara libyara-dev tesseract-ocr libzbar0 exiftool
```

**Windows:**
- YARA: prebuilt binaries are bundled inside `yara-python`, so `pip install yara-python` alone is usually sufficient.
- Tesseract OCR: install from https://github.com/UB-Mannheim/tesseract/wiki and set `TESSERACT_CMD` in `.env` to the installed `tesseract.exe` path.
- zbar (for QR/pyzbar): download the DLLs from https://sourceforge.net/projects/zbar/ and ensure they're on `PATH`, or install via `pip install pyzbar-x` variants that bundle the DLL.
- ExifTool: download from https://exiftool.org and set `EXIFTOOL_CMD` if you extend metadata analysis to shell out to it (the default implementation uses Pillow's built-in EXIF reader, so ExifTool is optional).

If any of these tools are missing, HATA does **not** crash — every module reports
itself as "unavailable" in the scan result and the rest of the pipeline continues.

### Backend setup
```bash
cd backend
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
# edit .env: set SECRET_KEY, optionally AI_API_KEY, GMAIL_* or leave IMAP defaults

uvicorn app.main:app --reload --port 8000
```
The API is now live at `http://localhost:8000`. Tables are created automatically
on first run (SQLite by default at `backend/hata.db`).

### Frontend setup
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173`. The Vite dev server proxies `/api` and `/ws` to
the backend on port 8000 (see `vite.config.js`).

### Logging in
The dashboard is behind a single-tenant login screen. The default password is
**`operationhata`**, set via `ACCESS_PASSWORD` in `backend/.env` — change it
there. This is intentionally a lightweight single-password gate (not a
multi-user identity system) appropriate for a single-operator security
console; see §18 for the reasoning and how to extend it.

### Try it immediately with Demo Mode
From the Dashboard, click **"Load Demo Data"** (or `POST /api/demo/seed`) to
populate the dashboard with clearly-labeled synthetic scans spanning
SAFE → CRITICAL, so every page can be explored without connecting Gmail.

---

## 5. Environment Variables (`backend/.env`)

See `backend/.env.example` for the full list. Key variables:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Used to derive the Fernet key that encrypts stored email credentials |
| `DATABASE_URL` | `sqlite:///./hata.db` (default) or a `postgresql+psycopg2://...` URL |
| `AI_API_KEY` | Anthropic API key. If unset, AI reports fall back to a deterministic technical summary |
| `AI_MODEL` | Defaults to `claude-sonnet-4-6` |
| `VIRUSTOTAL_API_KEY` | Optional. If unset, hash/URL reputation shows "Not Configured" instead of failing |
| `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` | For a future OAuth2 integration (see §8) |
| `IMAP_HOST` / `IMAP_PORT` | Used by the default Gmail App-Password IMAP integration |
| `MAX_UPLOAD_MB` | Manual/automatic attachment size limit |
| `ACCESS_PASSWORD` | Console login password (default `operationhata` — change this) |

**No secret is ever hardcoded**, and API keys are never sent to the frontend —
the Settings page only shows a boolean "configured / not configured" flag.

---

## 6. Database Setup

**SQLite (default):** nothing to do — the file is created automatically at
`backend/hata.db` on first run.

**PostgreSQL (production):**
```bash
createdb hata_db
createuser hata_user --pwprompt
```
Then set in `.env`:
```
DATABASE_URL=postgresql+psycopg2://hata_user:password@localhost:5432/hata_db
```
The SQLAlchemy models in `app/models/models.py` are identical for both backends.

---

## 7. AI Setup

1. Get an Anthropic API key.
2. Set `AI_API_KEY` in `backend/.env`.
3. Restart the backend.

If this step is skipped, HATA is still fully functional: the risk engine still
scores every scan from deterministic evidence, and a clearly-labeled non-AI
fallback report ("AI analysis unavailable. Technical risk assessment is still
available.") is generated instead — see `app/services/ai_analyzer.py`.

---

## 8. Gmail Setup

The reference implementation authenticates via **IMAP with a Gmail App
Password** — simpler to set up for a demo/coursework environment than a full
OAuth consent screen, and credentials are still never stored in plaintext
(encrypted with Fernet, derived from `SECRET_KEY`, before being written to the
database).

1. Enable 2-Step Verification on the Gmail account.
2. Go to **myaccount.google.com → Security → App Passwords** and generate one.
3. In HATA, go to **Automatic Monitoring**, enter the Gmail address and the
   16-character app password, and click **Connect Gmail**.
4. Click **START MONITORING**.

**OAuth2 (production path):** the codebase already includes the credential
storage model needed for OAuth (`EmailAccount.encrypted_credential` can hold
an encrypted refresh token just as easily as an app password) and a
`GMAIL_CLIENT_ID`/`GMAIL_CLIENT_SECRET`/`GMAIL_REDIRECT_URI` config surface.
To complete OAuth2, register credentials in Google Cloud Console, implement
the `/api/emails/oauth/callback` exchange, and swap the IMAP fetch in
`app/services/email_monitor.py` for a Gmail API client — the rest of the
pipeline (quarantine → analysis → risk → AI → report) is unchanged.

---

## 9. YARA Setup

`yara-python` is installed via `requirements.txt`. Rules live under
`backend/rules/yara/{images,generic,suspicious,embedded}/*.yar` and are
auto-compiled and loaded on first scan. Add new `.yar` files to any
subdirectory and they'll be picked up automatically (server restart required
to recompile). If `yara-python` fails to install on your platform, the YARA
stage simply reports `engine_available: false` and the rest of the scan
proceeds normally.

---

## 10. OCR Setup

Install the Tesseract binary (see §4). `pytesseract` (the Python wrapper) is
already in `requirements.txt`. If Tesseract isn't on `PATH`, set
`TESSERACT_CMD` in `.env` to its full path. Without it, the OCR card in the
scan result clearly shows "OCR analysis unavailable" rather than fabricating
a result.

---

## 11. Running the Application

```bash
# Terminal 1
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```
Open `http://localhost:5173`.

---

## 12. Hosting / Deployment

The frontend and backend can be deployed to two different domains -
`services/api.js` reads `VITE_API_BASE_URL`/`VITE_WS_URL` at build time for
this, falling back to same-origin `/api` and `/ws` (used by the Vite dev
proxy) when unset.

### Push your code
```bash
git add .
git commit -m "Operation HATA"
git remote add origin <your-repo-url>   # skip if already added
git push -u origin main
```

### Deploy with Render (a `render.yaml` blueprint is included)
1. Push this repo to GitHub (see above).
2. On [render.com](https://render.com), click **New → Blueprint** and point it at your repo. Render reads `render.yaml` at the repo root and provisions:
   - `hata-backend` — a Python web service running Uvicorn
   - `hata-frontend` — a static site serving the Vite build
   - `hata-db` — a free managed PostgreSQL instance, wired into the backend automatically via `DATABASE_URL`
3. Set the values Render leaves blank (`sync: false` in `render.yaml`) in each service's **Environment** tab:
   - Backend: `ACCESS_PASSWORD`, `CORS_ORIGINS` (set to your frontend's Render URL, e.g. `https://hata-frontend.onrender.com`), and optionally `AI_API_KEY` / `VIRUSTOTAL_API_KEY`
   - Frontend: `VITE_API_BASE_URL` (your backend URL + `/api`) and `VITE_WS_URL` (your backend URL with `wss://` + `/ws`)
4. Redeploy the frontend after setting its env vars (static sites need a rebuild to pick up new `VITE_*` values).

**Free-tier disk caveat:** Render's free web service disk is ephemeral - files in `quarantine/` and `reports/` do not survive a redeploy or a spin-down/spin-up cycle, but all scan *data* (findings, risk scores, AI reports) lives in the attached Postgres database and is unaffected, since PDF generation reads from the database, not the original file. Re-scanning an attachment after a redeploy will fail gracefully (`410 Gone`) if its quarantined file was lost, rather than crashing.

Any other host that runs a standard Python ASGI app + a static site works the same way (Railway, Fly.io, a VPS with `uvicorn`/`nginx`, etc.) — the two environment variables above are the only thing that changes between them.

## 13. Testing

**Backend:**
```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```
Covers filename/path safety, magic-byte detection, signature mismatch
detection, hashing, entropy, the risk-scoring engine (including the 100-point
cap and category boundaries), and the full Scans API lifecycle (upload → start
→ retrieve, plus validation-error paths for oversized/invalid/empty files).

**Frontend:**
```bash
cd frontend
npx vitest run
```

---

## 14. API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/scans/upload` | Validate + quarantine an image |
| POST | `/api/scans/{id}/start` | Run the full analysis pipeline |
| GET | `/api/scans/{id}` | Full scan detail (all module results) |
| GET | `/api/scans` | List/filter/search scan history |
| GET | `/api/scans/{id}/report` | JSON report |
| GET | `/api/scans/{id}/report/pdf` | Download branded PDF report |
| GET | `/api/dashboard/stats` | SOC dashboard aggregate stats |
| GET | `/api/emails/status` | Email connection/monitoring status |
| POST | `/api/emails/connect` | Connect Gmail (IMAP app password) |
| POST | `/api/emails/start-monitoring` / `stop-monitoring` / `sync-now` | Monitoring lifecycle |
| GET | `/api/quarantine` | List quarantined items |
| DELETE | `/api/quarantine/{id}` | Permanently delete (requires `confirm: true`) |
| POST | `/api/quarantine/{id}/restore` | Restore (requires `confirm: true`, blocked for CRITICAL) |
| GET | `/api/notifications` | Notification feed |
| GET`/POST` | `/api/settings` | Scanner/AI/notification configuration |
| GET | `/api/threat-intel` | Aggregated threat patterns |
| POST | `/api/demo/seed` / `DELETE /api/demo/clear` | Demo data |
| WS | `/ws` | Real-time scan progress + notifications |

---

## 15. Database Overview

`users` are implicit (single-tenant demo); core tables: `email_accounts`,
`emails`, `attachments`, `scans`, `signature_results`, `file_hashes`,
`metadata_results`, `entropy_results`, `steganography_results`,
`embedded_content`, `yara_results`, `ocr_results`, `qr_results`,
`url_results`, `risk_assessments`, `ai_reports`, `quarantine_items`,
`notifications`, `user_settings`. Each analysis-module table has a foreign
key to `scans.id`; `scans` links to `attachments`, which optionally link to
`emails` (null for manual uploads). See `app/models/models.py` for the full
schema.

---

## 16. Troubleshooting

**"ERROR: Failed to build wheel for yara-python" on Windows during `pip install`:**
This requires Microsoft C++ Build Tools to compile. YARA is optional — open
`requirements.txt`, comment out (`#`) the `yara-python` line, and re-run
`pip install -r requirements.txt`. The YARA card in scan results will show
"unavailable" instead of running real rules, but everything else works fully.
The same applies to `pyzbar` (QR detection) and `opencv-python-headless` if
they fail to build.

**A page shows a red "Something went wrong" panel:** click "Try Again". If it
persists, look at the **backend terminal window** at that exact moment — every
unhandled error is logged there with a full stack trace, and the panel's
message field mirrors the top line of that error.

**Getting a generic 500 error on some action:** as of this build, every
unhandled exception returns a readable JSON message (rather than an opaque
failure) and is always printed with a full traceback to the backend console —
copy that traceback if you need help diagnosing further.

**Logged out unexpectedly / "Not authenticated":** the login token is held in
memory on the backend and is cleared if the backend process restarts (e.g.
`--reload` picked up a code change). Just log in again.

## 17. Security Considerations

- Uploaded files are validated by **magic bytes**, not extension or declared MIME type.
- Filenames are sanitized and replaced with randomly generated names before storage; the original name is preserved only as metadata.
- All quarantine paths are checked against path-traversal via `is_within_directory()`.
- Files are **never executed** at any point in the pipeline.
- File size and count are capped (`MAX_UPLOAD_MB`).
- Destructive quarantine actions (delete) require an explicit `confirm: true`; CRITICAL-risk files cannot be restored via the API.
- Email credentials are encrypted at rest (Fernet, keyed from `SECRET_KEY`) and never returned to the frontend.
- CORS is restricted to configured origins (`CORS_ORIGINS`).
- API keys are read only from server-side environment variables and are never exposed in API responses (only a boolean "configured" flag is returned).
- Structured logs are emitted for every pipeline stage (`app/services/scan_orchestrator.py`) for auditability.

---

## 18. Limitations

- Operation HATA is a **single-tenant security console** by design — one shared login password rather than multi-user accounts/roles, matching a personal or small-team security-lab context rather than a multi-tenant SaaS product. See §19 for how to extend this to real multi-user auth.
- Steganography and entropy findings are **statistical heuristics**, not proof — both false positives and false negatives are possible, and the UI/report language reflects this.
- The AI layer only interprets evidence already collected deterministically; it never independently "detects" malware and never overrides the computed risk score.
- Gmail integration ships with IMAP/App-Password auth by default; full OAuth2 requires the operator's own Google Cloud OAuth client credentials (architecture is in place, exchange flow is not implemented — see §8).
- YARA/OCR/QR modules degrade gracefully but obviously provide no signal if their underlying binaries aren't installed.
- VirusTotal integration is optional and rate-limited by VirusTotal's own free-tier limits if configured.
- This is a v1 focused on **image attachments only**, by design (see §19).

---

## 19. Future Enhancements

- `PDFAnalyzer`, `DocumentAnalyzer`, `ArchiveAnalyzer`, `VideoAnalyzer` for non-image attachment types (the `services/` module pattern already generalizes to this)
- Full Gmail OAuth2 + Outlook/Microsoft Graph support
- Multi-user auth (JWT) — current build is single-tenant by design for a security-lab/demo context
- Rate limiting middleware for public deployments
- Sandbox/detonation-chamber integration for dynamic analysis

---

## 20. Project Structure

```
backend/
  app/
    main.py, config.py
    api/            # scans, emails, dashboard, quarantine, notifications, settings, threat_intel, demo
    models/         # SQLAlchemy models
    schemas/        # Pydantic request schemas
    services/       # every analysis module + orchestrator + email monitor + report generator
    database/       # engine/session
    utils/          # security (filenames/paths), crypto, serializers
  quarantine/       # isolated per-scan storage (gitignored contents)
  reports/          # generated PDFs (gitignored contents)
  rules/yara/       # modular YARA rule directories
  tests/            # pytest suite

frontend/
  src/
    components/     # layout, dashboard, scanner, common
    pages/          # Dashboard, ManualScan, ScanResult, AutomaticMonitoring, History, Reports, Quarantine, ThreatIntelligence, Settings
    services/api.js # centralized Axios client
    hooks/          # WebSocket hook
    context/        # notification context
    utils/          # risk color/icon mapping
  tests/            # vitest suite
```

---

*Operation HATA — built as a demonstrable, end-to-end security engineering project. Every module listed above is real, tested code — not placeholder UI.*
