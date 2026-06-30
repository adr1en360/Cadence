# Tests Workspace

## What This Workspace Is For
All tests for Cadence — unit tests for services and models, integration tests for API routes, and sandbox end-to-end tests that hit real Nomba sandbox endpoints.

## Process
1. Write unit tests for services (billing, dunning, webhook) with mocked Nomba client
2. Write integration tests for API routes using FastAPI's TestClient
3. Write sandbox e2e tests using real test credentials (checkout creation, payment verification)
4. Run with `pytest` from the project root

## Files In Here

```
tests/
├── __init__.py
├── conftest.py                 ← Shared fixtures (test DB, mock Nomba client, test merchant)
├── test_billing_service.py     ← State machine transitions, subscription creation
├── test_dunning_service.py     ← Retry logic, escalation timing, skip-locked behavior
├── test_webhook_service.py     ← HMAC verification, event dispatch, signature generation
├── test_nomba_client.py        ← Token refresh, environment-aware path switching
├── test_api_plans.py           ← Plan CRUD endpoints
├── test_api_subscriptions.py   ← Subscription lifecycle endpoints
└── test_sandbox_e2e.py         ← Real sandbox calls (requires NOMBA_TEST_* env vars)
```

## What Good Output Looks Like
- Unit tests mock external dependencies (Nomba API, email)
- Integration tests use an in-memory or test database
- Sandbox e2e tests are marked with `@pytest.mark.sandbox` so they can be skipped in CI
- Every billing state transition has at least one test
- Test names describe the scenario: `test_subscription_transitions_to_past_due_after_failed_payment`

## Constraints
- Never use production credentials in tests
- Sandbox e2e tests use `NOMBA_TEST_CLIENT_ID` and `NOMBA_TEST_CLIENT_SECRET` env vars
- Tests must not depend on execution order

_Last updated: 2026-06-30_
