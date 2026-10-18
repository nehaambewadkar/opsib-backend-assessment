# OPSiB Backend Assessment

A Python backend for retail operations exception management. It processes purchase orders and goods receipts, detects actionable receipt shortfalls, routes tasks to eligible employees, and records task progress through an auditable history.

## Features

- CSV fixture processing and duplicate source-record handling
- Product and location alias mapping
- Base-unit quantity conversion
- Deterministic shortfall detection using the frozen evaluation time
- Employee routing based on employment status, role, location, and shift
- PostgreSQL persistence for purchase orders, exceptions, tasks, and audit events
- FastAPI endpoints for exceptions and tasks
- Validated task status transitions
- Automated pytest suite

## Technology Stack

- Python 3.12
- FastAPI and Uvicorn
- SQLAlchemy
- PostgreSQL
- Pydantic Settings
- pytest

## Architecture and Data Flow

1. **Ingestion:** Read the supplied synthetic CSV fixtures and validate required columns and source identities.
2. **Mapping:** Normalize source product and location identifiers through the supplied alias files.
3. **Reconciliation:** Convert quantities into the product's base unit, aggregate posted receipts without counting duplicate source records twice, and compare accepted quantities with eligible purchase-order lines.
4. **Detection:** Use the fixed evaluation time of `2026-10-16 15:00:00 Asia/Kolkata`. A shortfall is actionable only after the expected receipt deadline has passed and the PO line is not cancelled.
5. **Routing:** Select an eligible employee according to employment, role, location, and workforce shift data.
6. **Persistence and workflow:** Store exceptions and tasks in PostgreSQL and record task status transitions in an audit history.

A receipt shortfall does not by itself prove supplier fault. The supplied fixtures do not contain supplier dispatch or advance shipping notice (ASN) evidence.

## Project Structure

```text
opsib-backend-assessment/
├── app/
│   ├── db/
│   ├── detection/
│   ├── ingestion/
│   ├── mapping/
│   ├── routing/
│   ├── workflows/
│   └── main.py
├── fixtures/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.12
- PostgreSQL
- Git

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/nehaambewadkar/opsib-backend-assessment.git
cd opsib-backend-assessment
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create a PostgreSQL database named `opsib_assessment`.

Create a `.env` file in the project root. Use the database URL setting expected by `app/config.py`, for example:

```text
DATABASE_URL=postgresql+psycopg://USERNAME:YOUR_PASSWORD@localhost:5432/opsib_assessment
```

Replace the placeholders with your own local credentials. Never commit `.env` or real credentials.

### 5. Initialize the database

```powershell
python -m app.db.init_db
```

This initializes the application's tables. The current project uses SQLAlchemy table creation; a production deployment should use a versioned migration system such as Alembic.

## Run the Fixture Pipeline

From the project root:

```powershell
python -m app.workflows.run_pipeline
```

The pipeline processes the supplied fixtures and persists actionable exceptions and tasks.

## Run the API

```powershell
python -m uvicorn app.main:app --reload
```

Available endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Root endpoint |
| GET | `/health` | Health check |
| GET | `/exceptions` | List exceptions |
| GET | `/tasks` | List tasks |
| GET | `/tasks/{task_id}` | Inspect a task |
| PATCH | `/tasks/{task_id}/status` | Request a validated task status transition |

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### Example requests

List exceptions:

```bash
curl http://127.0.0.1:8000/exceptions
```

List tasks:

```bash
curl http://127.0.0.1:8000/tasks
```

Update a task status using the request schema exposed by Swagger:

```json
{
  "new_status": "IN_PROGRESS",
  "actor_id": "HR-102",
  "reason": "Started investigating receipt shortfall"
}
```

Use an existing task ID and a transition allowed from that task's current state. A completed or otherwise terminal task cannot be arbitrarily reopened.

## Expected Fixture Outcomes

| Purchase order | Expected interpretation |
|---|---|
| PO-501 | Shortfall of 8 EA |
| PO-502 | No shortfall |
| PO-503 | Deadline not yet passed at evaluation time |
| PO-504 | Cancelled; excluded from shortfall detection |
| PO-505 | 10 BOX = 120 EA ordered; 96 EA accepted; shortfall of 24 EA |
| PO-506 | Duplicate receipt source record counted once; shortfall of 10 EA |

These findings describe receipt shortfalls, not proven supplier or carrier fault.

## Run Tests

```powershell
python -m pytest -q
```

The test suite previously passed with 35 tests. Run the command above to verify the current checkout.

Check dependency consistency:

```powershell
python -m pip check
```

## Data Model and Persistence

The application defines SQLAlchemy models for:

- `purchase_order_lines`
- `exceptions`
- `tasks`
- `task_audit_events`

The fixture pipeline persists purchase-order facts, exception records, task records, and task status audit events in PostgreSQL.

## Assumptions and Limitations

- The provided datasets are synthetic and are used as the assessment input.
- Business deadline decisions use the specified frozen evaluation time rather than the machine clock.
- Shortfall detection is deterministic and does not rely on an AI model for quantity calculations.
- The supplied data does not establish supplier dispatch quantities or prove where a shortage occurred.
- The current service is an assessment implementation, not a production multi-tenant platform.
- Versioned database migrations, authentication and authorization, tenant isolation, structured operational monitoring, and production secret management require further hardening.
- Import-level row rejection reports, conflicting-source-ID workflows, and full source-to-finding lineage should only be described as implemented where the code demonstrably supports them.

## Security

- Keep `.env` and its credentials private.
- Use placeholder values in `.env.example`.
- Do not commit virtual environments, caches, or local secrets.
- Use only the supplied synthetic fixture data.

## AI Tooling Disclosure

Complete this section accurately before submitting.

AI tools used: [Name the tools actually used, if any].

I reviewed and tested the implementation, including the fixture scenarios, database persistence, employee routing, task state transitions, and automated tests. I will explain the implemented behavior, limitations, and design trade-offs during the technical walkthrough. [Edit this statement to reflect the parts you personally reviewed, understood, and changed.]

## Running the Project from a Clean Checkout

1. Install Python dependencies.
2. Configure PostgreSQL and create the database.
3. Create `.env` with the required database URL.
4. Initialize database tables.
5. Run the fixture pipeline.
6. Start the FastAPI service.
7. Run the tests with `python -m pytest -q`.
