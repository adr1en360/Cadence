# Docs Workspace

## What This Workspace Is For
Architecture documentation, Nomba API integration notes, and design decisions. This is the reference material that informs how the code in `app/` should be built.

## Process
1. Document Nomba API findings as they're discovered (endpoint paths, auth flows, webhook schemas)
2. Record architecture decisions that affect multiple modules
3. Keep the Nomba API reference updated as we learn more from sandbox testing

## Files In Here

```
docs/
├── CONTEXT.md                  ← this file
├── architecture.md             ← System overview, component diagram, data flow
├── nomba_api.md                ← Nomba API reference (endpoints, auth, webhook format, gotchas)
├── nomba_api_llms.md           ← Nomba API LLM documentation index (for AI lookup)
├── billing_states.md           ← State machine diagram and transition rules
└── deployment.md               ← Render setup, env vars, Supabase config
```

## What Good Output Looks Like
- `nomba_api.md` has the exact sandbox vs production paths, auth header format, HMAC signing recipe
- `billing_states.md` has a mermaid state diagram that matches the code
- Docs reference actual code files when describing implementation details

## Constraints
- No credentials in docs — reference env var names only
- Keep docs in sync with code — stale docs are worse than no docs

## Nomba API Reference Guide (For AI Assistants)
- Refer to `docs/nomba_api_llms.md` for URLs of the latest Nomba API docs.
- Use the `read_url_content` tool to fetch live endpoint details from those URLs when you need exact schemas.

_Last updated: 2026-06-30_
