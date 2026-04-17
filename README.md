# issue-agent-test

A minimal Python web app used as a test repository for the issue-agent system.

## Structure

- `src/auth.py` — Authentication: password hashing, token generation
- `src/validators.py` — Input validation: username, password, email
- `src/database.py` — SQLite database operations
- `src/api.py` — Flask REST API endpoints
- `src/utils.py` — Utility helpers: retry, pagination, sanitization
- `tests/` — pytest test suite

## Setup

```bash
pip install flask pytest
python -c "from src.database import init_db; init_db()"
flask --app src.api run
```
