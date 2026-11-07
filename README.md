# SWASTI — 360° Human Wellness & Life Balance

*Balance Within. Harmony Around. Well-being for All.*

A full-stack, privacy-first wellness platform. It assesses 14 dimensions of life independently, runs 14 specialised, evidence-linked agents, and helps people make sustainable progress through micro-habits and quarterly reviews.

> **Status:** working end-to-end. 29 backend tests (unit, API, DB-integrity, migration) and 2 browser journeys pass against PostgreSQL 16. Demo data is clearly marked **synthetic**.

---

## Five design principles (enforced in code)

| Principle | How it is enforced |
|---|---|
| **No single headline score** | All 14 scores are always shown separately. The overall indicator is secondary and hidden when fewer than 10 dimensions are scored. "Needs Attention" dimensions are always listed on their own (`services/scoring.py`, dashboard). |
| **Short assessments** | 4 questions per dimension (56 total), on a common 1–5 scale. "Not applicable" and "Prefer not to answer" are excluded, never counted as zero. |
| **Evidence-driven agents** | Agents choose only from a curated knowledge base. Every recommendation has a foreign key to a `scientific_references` row. Optional LLM wording can only rephrase, and is labelled AI-generated. |
| **Privacy** | Coaches and counsellors need an explicit, scoped, revocable `access_grant`. Admins cannot open individual data. Analytics are aggregated with a minimum group size of 5. Every access and denial is audit-logged. |
| **Progress, not perfection** | Targets are capped at +10 points per quarter. Habit tracking has no streak penalties, and skipping is encouraged where it helps. |

## Architecture

```
frontend/ (React 19 + TS + Vite + Tailwind + Recharts, PWA)
   │  REST /api  (JWT bearer)
backend/  (FastAPI modular monolith)
   ├─ routers/       auth · privacy/consent · assessments & agents · interviews · wellness · portal/admin
   ├─ services/
   │   ├─ scoring.py        transparent weighted scoring, configurable bands
   │   ├─ assessment.py     transactional submission (atomic)
   │   ├─ agents.py         14 specialised agent classes (one per dimension)
   │   ├─ orchestrator.py   parallel execution, retries, logs, cross-wellness insights
   │   ├─ dashboard.py / reviews.py / reports.py (PDF) / safety.py (crisis guidance)
   │   └─ access.py / audit.py / crypto.py (encrypted transcripts)
   ├─ seed/          master data: 14 categories, 56 questions, 32 references, 43 recommendations
   ├─ migrations/    Alembic
   └─ sql/row_level_security.sql   optional Postgres RLS backstop (Supabase-ready)
PostgreSQL 16  (26 tables, UUID PKs, FKs, check constraints, indexes)
```

The API has no frontend-specific logic, so a future React Native app can use the same endpoints (OpenAPI: `docs/openapi.json`, live at `/docs`). The agents are plain classes behind `get_agent()`, so each one can later move into its own worker or microservice.

### Agent pipeline
For each dimension, an agent:
1. fetches the responses and history;
2. recalculates the score with the shared engine;
3. finds item-level strengths (≥ 75) and growth areas (≤ 50);
4. compares the score with the configurable benchmark and sets an achievable target;
5. ranks recommendations by how well they address the weakest items;
6. attaches micro-habits and evidence;
7. saves structured JSON to `agent_assessments`.

The orchestrator runs all active agents in a thread pool, each with its own database session. A failing agent is retried up to 3 times with backoff and every attempt is logged, so one failure never blocks the others. The orchestrator then derives cross-wellness insights ("these moved together — not a cause"). Insights never change scores, and each dimension appears in at most two of them.

Specialisations include:
* **Mental / Psychological:** crisis escalation to human resources.
* **Financial:** never recommends products.
* **Spiritual:** belief-neutral wording.
* **Sporting:** no performance comparison.

## Quick start with Docker (one command)

With Docker Desktop running:

```bash
git clone https://github.com/ajeygotkhindikar-web/swasti.git && cd swasti
```

macOS / Linux:

```bash
./start.sh
```

Windows (PowerShell):

```bash
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

On the first run, the script creates `.env` with fresh secrets and the synthetic demo data turned on. It then builds and starts the containers and opens http://localhost:8080. Log in with any demo account (password `Demo@1234`). To stop, run `docker compose down`; add `-v` to also wipe the data.

## Quick start (development)

Requires Python 3.11+, Node 20+, PostgreSQL 14+.

```bash
createdb swasti && createdb swasti_test
```

```bash
cd backend && pip install -r requirements.txt
```

```bash
alembic upgrade head && python -m app.seed.seed --demo
```

```bash
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. API docs are at http://localhost:8000/docs. Set `DATABASE_URL` if PostgreSQL is not at `postgresql+psycopg://postgres@localhost:5432/swasti`.

**Synthetic demo accounts** (password `Demo@1234`):

* `priya@swasti.demo` — individual with 3 quarters of history, habits and a review
* `coach@swasti.demo` — coach with consent from Priya
* `counselor@swasti.demo` — counsellor with consent from Priya
* `admin@swasti.demo` — administrator
* `ravi@swasti.demo` — individual who has *not* granted consent (to demonstrate access denial)

## Tests

```bash
cd backend && python -m pytest -q
```

This runs scoring unit tests, API journey tests, consent and access tests, DB-integrity tests, agent retry tests, and a check that the migration matches the models. It needs the `swasti_test` database.

For the browser journeys, start the API and `npm run build && npx vite preview`, then:

```bash
node e2e/journey.e2e.cjs
```

## Deployment

```bash
cp .env.example .env
```

Fill in `JWT_SECRET` and `TRANSCRIPT_ENCRYPTION_KEY`, then:

```bash
docker compose up --build
```

The web app is served at http://localhost:8080. The API container applies migrations and master data on start. Set `SEED_FLAGS=--demo` only for demonstrations.

For production (AWS, Azure or Supabase):
* Use managed PostgreSQL with encryption at rest.
* Terminate TLS at the load balancer.
* Store secrets in a secrets manager.
* Run the API as a non-superuser DB role and apply `backend/sql/row_level_security.sql`.
* Schedule `POST /api/admin/notifications/run` daily.
* Put rate limiting in a shared store. The login limiter is currently in-memory.

## Navigation (14 sections)
Home · My Profile · Wellness Assessment · Interview Assessment · 360° Wellness Dashboard · Wellness AI Agents · My Recommendations · Micro-Habits · Quarterly Reviews · Wellness Reports · Coach/Counsellor Portal · Administration · Privacy & Consent · Help & Resources. Each role sees only its own sections.

## Things to know before going live

* **Evidence links are not yet verified.** This build environment had no internet access, so the 32 reference URLs (WHO, ILO, MoHFW, RBI, SEBI, NCFE, MoEFCC, UNESCO, UNICEF, peer-reviewed DOIs) are seeded as `pending_verification`. A domain expert should check each one under **Administration → Evidence**, which records the verification date.
* **Thresholds are provisional.** The level bands (0–39 … 90–100) and the 56 questions are application indicators, not clinically validated instruments. They are editable in Administration and should be reviewed by qualified experts.
* **DPDP Act.** The app has the technical controls: consent records with versioning and withdrawal, data export, erasure, minimisation, audit, and encryption of transcripts. Legal compliance still needs a privacy notice and legal review, plus a Data Protection Officer or grievance process.
* **Optional features:**
  * AI rephrasing needs `ANTHROPIC_API_KEY` and per-user consent. Only scores and dimension names are sent.
  * Voice-to-text uses the browser Speech Recognition API where available.
  * The service worker handles push events, but sending push messages needs a VAPID push service, which is not included.
* **UI components.** The UI uses Tailwind with a small in-house component set (`components/ui.tsx`) rather than shadcn/ui.
