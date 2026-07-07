# Tests Workspace

## What This Workspace Is For
All tests for Cadence — unit tests, integration tests for API routes, and database/auth connectivity tests.

## Process
1. Write/modify tests in the `tests/` folder
2. Run tests with `pytest` from the project root

## Files In Here

```
tests/
├── __init__.py
├── CONTEXT.md                 ← this file
├── test_api_key.py            ← Tests for merchant API key generation and hashing
├── test_core_services.py      ← Tests for billing/dunning services, checkout, state transitions
├── test_db_connection.py      ← Verifies connection to the database
├── test_nomba_auth.py         ← Tests Nomba auth token issuance and caching
└── test_webhook_hmac.py       ← Tests webhook signature verification logic
```

## What Good Output Looks Like
- Unit tests mock external dependencies (Nomba API, email)
- Integration tests use a test database configuration
- Every billing state transition has at least one test
- Test names describe the scenario clearly

## Constraints
- Never use production credentials in tests
- Tests must not depend on execution order

_Last updated: 2026-07-07_
