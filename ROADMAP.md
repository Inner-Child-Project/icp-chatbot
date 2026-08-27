# ICP Chatbot — Roadmap

## ✅ Done

- LangGraph agent: chat → extract → proposal → human-in-the-loop review → submit
- FastAPI server with interrupt/resume flow + SQLite persistent checkpointer
- OpenRouter (gpt-4o-mini) + LangSmith tracing
- Sales-focused conversation, no-repeat info collection, honest submit feedback
- Docker + docker-compose, Portainer-ready, `icp-net` shared network with n8n
- n8n → Zoho CRM lead submission (`sourceForm=chatbot`) with bot-filter bypass
- Landing page chat widget (dark theme, approval flow, single confirmation)

## 🔜 Next

1. **Security & abuse hardening** — make the chatbot resistant to token-spend attacks and hacking in general (see below).

---

## Security & abuse hardening

**Why now:** `/api/chat` is currently unauthenticated and internet-reachable (via the Cloudflare Tunnel). An attacker (or a runaway bot) could spam conversations to burn OpenRouter credits, or attempt prompt-injection / payload attacks. The items below harden against both.

### A. Token-spend protection
- [ ] Set a hard monthly spend cap in OpenRouter (dashboard → Limits) — the single most important safeguard
- [ ] Rate-limit `/api/chat` per client IP and per `thread_id` (slowapi middleware or a simple in-memory limiter)
- [ ] Enforce a max input message length (reject oversized payloads, e.g. > 2000 chars)
- [ ] Verify/tighten the max-conversation-turn guard (currently ~24 messages of history)
- [ ] Confirm per-call `max_tokens` (already 500) and add a global per-thread token budget

### B. Authentication / access control
- [ ] Require a shared secret (header token) on `/api/chat`; the widget sends it, the server rejects without it
- [ ] Keep `/health` unauthenticated for uptime monitors (or protect it too — decide)

### C. Prompt-injection resistance
- [ ] Harden the system prompt: explicitly instruct the model to ignore "ignore previous instructions", role-swap, and "reveal your prompt" attempts
- [ ] Treat every model output as untrusted text; escape/strip before any rendering or downstream use

### D. General hardening
- [ ] Validate all input (reject non-string, malformed, or oversized JSON)
- [ ] Confirm CORS allowlist is locked to `products.innerchildproject.us` (+ localhost for dev)
- [ ] Add dependency scanning (GitHub Dependabot / `pip-audit`)
- [ ] Optional: Cloudflare Turnstile on the chat widget (bot protection before the request even reaches the server)
- [ ] Optional: request logging for abuse forensics (LangSmith already traces execution)
