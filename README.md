# OPSiB Backend Assessment

A backend application for retail operations exception management. The system processes purchase orders and goods receipts, detects actionable receipt shortfalls, assigns tasks to eligible employees, and maintains task audit history.

## Features

- CSV ingestion and duplicate source-record handling
- Product and location alias mapping
- Receipt shortfall detection using a fixed evaluation time
- Employee assignment based on status, shift, and role
- PostgreSQL persistence for purchase orders, exceptions, and tasks
- FastAPI endpoints for viewing exceptions and tasks
- Task status transitions with audit events
- Automated tests using pytest

## Technology Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic Settings
- pytest

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

Install the packages listed in your project's dependency file. If a `requirements.txt` file is added to the repository, use:

```powershell
pip install -r requirements.txt
```

### 4. Configure the database

Create a PostgreSQL database named `opsib_assessment`.

Create a `.env` file in the project root using the database URL setting expected by `app/config.py`:

```text
DATABASE_URL=postgresql+psycopg://USERNAME:YOUR_PASSWORD@localhost:5432/opsib_assessment
```

Replace the placeholders with your local PostgreSQL credentials. Do not commit `.env` or real credentials.

### 5. Initialize database tables

```powershell
python -m app.db.init_db
```

## Run the Pipeline

From the project root:

```powershell
python -m app.workflows.run_pipeline
```

The pipeline uses the fixed assessment evaluation time configured in the application and persists actionable exceptions and tasks.

## Run the API

```powershell
python -m uvicorn app.main:app --reload
```

The API is available at:

- Root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Exceptions: http://127.0.0.1:8000/exceptions
- Tasks: http://127.0.0.1:8000/tasks
- API documentation: http://127.0.0.1:8000/docs

## Run Tests

```powershell
python -m pytest -q
```

## Security

- Keep `.env` and database credentials private.
- Use `.env.example` only for placeholder configuration.
- Do not commit virtual environments, caches, or local secrets.

## Current Test Status

The project has previously passed 35 automated tests. Run the test command above to verify the current checkout.
