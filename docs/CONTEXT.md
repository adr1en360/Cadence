# Docs Workspace

## What This Workspace Is For
Architecture documentation, Nomba API integration notes, and design decisions. This is the reference material that informs how the code in `app/` should be built.

## Process
1. Document Nomba API findings as they're discovered (endpoint paths, auth flows, webhook schemas)
2. Record architecture decisions that affect multiple modules
3. Keep the Nomba API reference updated as we learn more from sandbox testing
4. Design and expose an `llms.txt` file for Cadence's own docs so integrating AI agents can easily understand how to use Cadence's API
5. Plan and package a custom agentic Skill (e.g. using `workflow-skill-creator`) once the subscription flow is fully functional and sandbox-tested to allow instant AI-driven platform integrations

## Files In Here

```
docs/
├── CONTEXT.md                  ← this file
├── developer_flow.md           ← High-level flow, integration guide, dashboard sections
├── api_surface.md              ← Developer public API surface endpoints reference
├── nomba_api.md                ← Nomba API reference (endpoints, auth, webhook format, gotchas)
├── nomba_api_llms.md           ← Nomba API LLM documentation index (for AI lookup)
├── billing_states.md           ← State machine diagram and transition rules
└── design_system.md            ← Brand colors, typography, layout tokens
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
