# AutoMerge

**Autonomous Debugging & Code-Fixing Platform**

AutoMerge is an AI-powered agent system that detects broken builds, analyzes logs, identifies root causes, generates fix patches, validates them in a sandbox, and presents everything in a premium dashboard.

![Status](https://img.shields.io/badge/status-active-brightgreen)
![Stack](https://img.shields.io/badge/stack-Next.js%20%2B%20FastAPI-blue)

## Features

- 🔍 **Failure Detection** — Ingest build/test logs and extract actionable signals
- 🧠 **Root Cause Analysis** — Classify failures and determine probable root cause with confidence scoring
- 🔧 **Auto-Patch Generation** — Generate code fixes with full diff visualization
- ✅ **Sandbox Validation** — Validate patches with simulated test execution
- 📊 **Premium Dashboard** — Real-time agent pipeline tracking with animated timeline
- 🧬 **Bug Memory** — Store recurring patterns and learn from past fixes
- 🎭 **Demo Mode** — One-click demo scenarios for live presentations
- 📝 **PR-Ready Summaries** — Generated pull request descriptions with reasoning traces

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+

### Backend

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — click **Demo** to trigger a scenario.

## Architecture

```
AutoMerge/
├── frontend/          # Next.js 16 + TypeScript + Tailwind
│   └── src/
│       ├── app/       # App Router pages
│       ├── components/# Dashboard, Agent, Diff, Logs
│       ├── hooks/     # Data fetching with polling
│       └── lib/       # API client, types, utils
├── backend/           # FastAPI + SQLAlchemy + SQLite
│   └── app/
│       ├── routes/    # REST endpoints
│       ├── services/  # Business logic
│       ├── agent/     # 7-step autonomous pipeline
│       ├── sandbox/   # Validation executor
│       └── demo/      # Sample failure data
```

## Agent Pipeline

1. **Log Parsing** — Clean and normalize raw logs
2. **Signal Extraction** — Detect error patterns and types
3. **Failure Classification** — Categorize into actionable types
4. **Root Cause Analysis** — Determine probable cause with confidence
5. **Patch Generation** — Create code fix with diff
6. **Patch Validation** — Run tests in sandbox
7. **Summary Generation** — Produce PR-ready description

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health check |
| GET | `/api/diagnostics` | System statistics |
| GET | `/api/jobs` | List all fix jobs |
| GET | `/api/jobs/:id` | Job detail with full pipeline |
| POST | `/api/failures` | Ingest a new failure |
| POST | `/api/demo/trigger` | Trigger demo scenario |
| DELETE | `/api/jobs/:id` | Delete a job |

## License

MIT
