# ASTRA HEALTH

A locally runnable research prototype for monitoring synthetic astronaut health data. The mission, crew, measurements, and alert thresholds are fictional. The application has no clinical validation.

## Run locally

Prerequisites are Python 3.10+ and Node.js 20+. Run these commands from this directory in PowerShell.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
npm ci
npm run build
.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. FastAPI serves the compiled UI and API. SQLite is created on first launch and seeded with 14 readings per astronaut. For frontend development, run `npm run dev` in a second terminal and open the Vite URL. API documentation is at http://127.0.0.1:8000/docs.

## Accounts and Synthetic Demo

Create an account from the sign-in screen. Account settings lets you edit your name, mission, role, start date, and personal baselines. Private accounts start with empty history and unset baselines. Save a check-in from the dashboard.

Choose **Enter Synthetic Demo** on the sign-in screen to see three read-only scenarios. Elena Voss has stable readings, Amara Chen shows declining sleep and rising fatigue, and Mateo Silva shows a rise in resting heart rate with reported symptoms.

## Sessions and data isolation

Passwords use Argon2id. The browser holds an opaque HttpOnly, SameSite=Strict session cookie. SQLite holds only the token digest. Sessions expire after eight hours, and logout revokes the active session on the server. The server limits sign-in and registration attempts per IP in memory. These limits reset when the process restarts and are scoped to one server process.

Private API routes are under `/api/me`. Each route derives its owner from the validated session. The demo routes read separate synthetic tables. On startup, SQLAlchemy creates missing tables. The original `astronauts` and `readings` tables remain in place without modification. The new demo tables are seeded from the bundled synthetic scenarios, so older demo edits are retained in the legacy tables without being published or assigned to a new account.

For HTTPS, the cookie is marked Secure automatically when FastAPI sees the HTTPS scheme. For TLS termination behind a trusted proxy, configure trusted forwarded headers, set `ASTRA_SECURE_COOKIES=1`, and set `ASTRA_ORIGIN` to the public HTTPS origin. Keep the development server on loopback. SQLite is not encrypted at rest.

## Cloud AI and offline use

Copy `.env.example` to `.env`, set `GEMINI_API_KEY`, and restart FastAPI. Enable the consent checkbox before requesting AI analysis, chat, or a daily report. Google Gemini receives the active profile's metrics, alerts, up to 14 recent check-ins (including notes), and the question. The server does not send account email, name, or mission metadata as separate fields. Avoid identifying information in free-text notes or questions. Turning consent off blocks new requests from the UI.

Private AI results are stored under the account. The UI reloads the latest 50 AI entries, including the latest saved analysis and report among those entries. Daily reports can be downloaded as text. Downloaded files are managed by the operating system.

Core monitoring works without internet while the local server is running. The production build caches the app shell and synthetic snapshots for server-offline viewing. Private records are kept out of browser persistent storage and require a reachable local server to load.

Google Gemini uses the configured model only, with one attempt per request. Free-tier availability depends on your Google project. Keep it on the free tier and use synthetic records for cloud demos. Free-tier content may be used by Google to improve its products.

## Demo alert rules

Baseline offsets compare the latest measurement to the personal baseline, when set. Per-metric thresholds are in `backend/thresholds.json`. A crew review flag fires for elevated resting heart rate with reported symptoms, or reduced sleep with elevated fatigue. A data-gap flag fires for blank measurements or a latest check-in older than 36 hours. Recent trend compares the latest three valid readings to earlier valid readings among the latest seven check-ins. These thresholds are for software demonstration and have no clinical validation.

NASA references are curated in `backend/ai.py`. Retrieval ranks reference tags against the question and alert codes. The server resolves returned citations against the retrieved source IDs.

## Tests

```powershell
.venv/Scripts/python -m pytest -q
npm run build
```

