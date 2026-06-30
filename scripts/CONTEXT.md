# Scripts Workspace

## What This Workspace Is For
Developer utilities for local development and sandbox testing. These are NOT part of the production app — they're tools for us to test Nomba integrations, seed data, and debug webhooks.

## Process
1. Use scripts to test Nomba sandbox flows locally (create checkout, receive webhook, verify transaction)
2. Use seed scripts to populate the dev database with test merchants, plans, and subscriptions
3. Run migration scripts through Alembic

## Files In Here

```
scripts/
├── CONTEXT.md                  ← this file
├── create_checkout.py          ← Creates a tokenized sandbox checkout order (already exists)
├── webhook_receiver.py         ← Local webhook listener that logs payloads (already exists)
├── seed_data.py                ← Populate dev DB with test merchant, plans, subscriptions
└── test_nomba_auth.py          ← Quick auth token test (verify credentials work)
```

## What Good Output Looks Like
- Scripts are standalone — run with `python scripts/<name>.py`, no app server needed
- Scripts load credentials from env vars or `.env` file, never hardcoded
- Output is clear and human-readable (print what's happening at each step)

## Constraints
- Never commit `.env` files — use `.env.example` as a template
- Scripts use `urllib` or `httpx` directly, not the app's `nomba_client.py` (they're independent)

_Last updated: 2026-06-30_
