# App Workspace

## What This Workspace Is For
The core Cadence application. Everything that runs in the FastAPI process lives here — API routes, the Nomba client, the billing state machine, the dunning scheduler, database models, and the Jinja2 templates for the merchant dashboard and subscriber portal.

## Process
1. **Models first** — define or update SQLAlchemy models in `models/`, then generate Alembic migration
2. **Services** — implement business logic in `services/` (billing engine, dunning, webhook processing)
3. **Core** — Nomba client, OAuth token manager, security utilities live in `core/`
4. **Routes** — expose via FastAPI routers in `api/`, wire to services
5. **Templates** — build Jinja2 pages in `templates/`, TailwindCSS via CDN

## Files In Here

```
app/
├── __init__.py
├── main.py                     ← FastAPI app factory & routers configuration
├── api/
│   ├── __init__.py
│   ├── router_auth.py          ← Merchant auth (login, API key generation)
│   ├── router_plans.py         ← CRUD subscription plans
│   ├── router_subscriptions.py ← Create/cancel/list subscriptions
│   ├── router_webhooks.py      ← Inbound Nomba webhooks processing
│   ├── router_dashboard.py     ← Merchant dashboard pages (Jinja2)
│   ├── router_portal.py        ← Subscriber self-service portal endpoints & page
│   └── deps.py                 ← Shared dependencies (DB session, current merchant)
├── core/
│   ├── __init__.py
│   ├── config.py               ← Settings via pydantic-settings (env vars)
│   ├── security.py             ← JWT, API key hashing, HMAC verification
│   ├── nomba_client.py         ← Environment-aware Nomba API client & OAuth token cache
│   └── database.py             ← SQLAlchemy database connection & session setup
├── models/
│   ├── __init__.py
│   ├── merchant.py             ← Merchant account + API keys
│   ├── plan.py                 ← Subscription plans (name, amount, interval)
│   ├── subscription.py         ← Subscription state machine (6 states)
│   ├── payment.py              ← Payment attempts + tokenized cards
│   └── event.py                ← Audit log (every state change, charge, webhook)
├── services/
│   ├── __init__.py
│   ├── billing_service.py      ← Create subscription, process payment outcomes
│   └── dunning_service.py      ← Retry scheduler logic (1d → 3d → 7d escalation)
├── templates/
│   ├── base.html               ← Shared layout (TailwindCSS CDN, dark theme)
│   ├── landing.html            ← Landing & features overview page
│   ├── login.html              ← Merchant dashboard login page
│   ├── register.html           ← Merchant registration & onboarding page
│   ├── dashboard.html          ← Integrated merchant operations dashboard
│   ├── portal.html             ← Integrated customer billing self-service portal
│   └── developer/              ← Developer portal documentation templates
│       ├── base.html
│       ├── introduction.html
│       ├── authentication.html
│       ├── plans.html
│       ├── subscriptions.html
│       ├── webhooks.html
│       └── errors.html
└── static/
    └── styles.css              ← Custom CSS overrides
```

## What Good Output Looks Like
- Every route handler is thin — it validates input, calls a service, returns a response
- All Nomba API calls go through `nomba_client.py`, never direct
- The billing state machine enforces valid transitions only (no jumping from `trialing` to `expired`)
- Dunning scheduler uses `FOR UPDATE SKIP LOCKED` — safe for concurrent runs
- Every state change creates an `Event` record in the audit log
- Templates extend `base.html`, use TailwindCSS utility classes, dark theme

## Constraints
- No raw SQL — use SQLAlchemy ORM everywhere
- No Nomba credentials in code — environment variables only (`NOMBA_CLIENT_ID`, `NOMBA_CLIENT_SECRET`, `NOMBA_ACCOUNT_ID`, `NOMBA_ENV`)
- Sandbox uses `/sandbox/checkout/` paths, production uses `/v1/checkout/` — the `nomba_client.py` switches based on `NOMBA_ENV`
- OAuth2 tokens expire in 30 minutes — `nomba_client.py` must refresh proactively
- Idempotency header is `X-Idempotent-key` (note exact casing)
- Webhook HMAC uses colon-delimited structured string, NOT raw body

_Last updated: 2026-06-30_
