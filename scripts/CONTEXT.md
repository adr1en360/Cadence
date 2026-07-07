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
├── create_checkout.py          ← Creates a tokenized sandbox checkout order
├── webhook_receiver.py         ← Local webhook listener that logs payloads
└── seed_data.py                ← Populate dev DB with test merchant, plans, subscriptions
```

## What Good Output Looks Like
- Scripts are standalone — run with `uv run scripts/<name>.py`, no app server needed
- Output is clear and human-readable (print what's happening at each step)

## Constraints
- Never commit `.env` files — use `.env.example` as a template

_Last updated: 2026-07-07_
