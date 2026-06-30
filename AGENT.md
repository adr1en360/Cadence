# Cadence

## Identity
Managed subscription billing engine built on Nomba's payment APIs for the Nigerian market.
Stack: FastAPI (Python), PostgreSQL (Supabase), Jinja2 + TailwindCSS, deployed on Render free tier.
Hackathon project (DevCareer × Nomba 2026, Infrastructure Track). Team: Eniolami Saheed and Adrien Oke
Reference merchant: SchoolPadi (student study tool, ₦1,500–2,000/month subscriptions).

## Folder Map

| Workspace | Purpose |
|-----------|---------|
| app/ | Core application — API routes, Nomba client, billing engine, models, templates |
| tests/ | Test suite — unit, integration, sandbox end-to-end |
| docs/ | Architecture docs, Nomba API findings, design decisions |
| scripts/ | Dev utilities — checkout testing, webhook receiver, DB seeding |

## Routing Table

| Task | Go To | Read | Tools/Skills |
|------|-------|------|--------------|
| Add/modify API endpoints | app/api/ | app/CONTEXT.md | — |
| Billing state machine, dunning logic | app/services/ | app/CONTEXT.md | — |
| Nomba API integration (auth, checkout, refund) | app/core/ | app/CONTEXT.md, docs/nomba_api.md | — |
| Database models or migrations | app/models/ | app/CONTEXT.md | alembic |
| Dashboard or portal UI | app/templates/ | app/CONTEXT.md | — |
| Write or run tests | tests/ | tests/CONTEXT.md | pytest |
| Document architecture or decisions | docs/ | docs/CONTEXT.md | — |
| Dev scripts, sandbox testing | scripts/ | scripts/CONTEXT.md | — |

## Naming Conventions
- Models: `snake_case.py` (e.g. `subscription.py`, `merchant.py`)
- API routes: `router_<resource>.py` (e.g. `router_subscriptions.py`)
- Services: `<domain>_service.py` (e.g. `billing_service.py`)
- Tests: `test_<module>.py`
- Docs: `<topic>.md` (e.g. `nomba_api.md`, `architecture.md`)
- Templates: `<page>.html` (e.g. `dashboard.html`, `portal.html`)
