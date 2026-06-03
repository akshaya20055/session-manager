# Session Manager

Production-ready FastAPI project for managing interview sessions.

## Features

- FastAPI application factory with health check
- SQLAlchemy 2.0 ORM model for `InterviewSession`
- SQLite database configuration through environment variables
- Pydantic V2 request and response schemas
- Alembic migrations
- Service layer for business logic
- Custom exception handling
- Pytest API test suite

## Project Structure

```text
app/
|-- main.py
|-- config.py
|-- database.py
|-- dependencies.py
|-- models/
|   `-- session.py
|-- schemas/
|   `-- session_schema.py
|-- routers/
|   `-- sessions.py
|-- services/
|   `-- session_service.py
|-- utils/
|   `-- logger.py
`-- exceptions/
    `-- custom_exceptions.py

tests/
```

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run database migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`.

## Endpoints

- `GET /health`
- `POST /api/v1/sessions/start`
- `GET /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `PUT /api/v1/sessions/{session_id}`
- `POST /api/v1/sessions/{session_id}/pause`
- `POST /api/v1/sessions/{session_id}/resume`
- `POST /api/v1/sessions/{session_id}/end`

## InterviewSession Model

- `id`: UUID primary key
- `candidate_id`: string
- `status`: `ACTIVE`, `PAUSED`, or `ENDED`
- `started_at`: datetime
- `updated_at`: datetime
- `ended_at`: nullable datetime
- `created_at`: datetime

## Concurrent Session Handling

- Duplicate `ACTIVE` sessions are prevented for the same candidate.
- Validation occurs before session creation.
- The current implementation is suitable for development and learning purposes.
- Production systems may require database locking or distributed coordination for high concurrency.

## Tests

Run the test suite:

```bash
pytest
```
