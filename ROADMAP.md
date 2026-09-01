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
  > Manual (not code): openrouter.ai → **Settings → Credits / Limits** → set **Monthly limit** (e.g. $10–$20 for dev, $50–$100 for prod) → enable **email alerts at 80%**. Also set **per-request max** if available. This is the only guard that survives a code bypass.
- [x] Rate-limit `/api/chat` per client IP and per `thread_id` (SlidingWindow 20/60s for each — `RATE_LIMIT` + `THREAD_RATE_LIMIT` in `.env.example`)
- [x] Enforce a max input message length (Pydantic `max_length=2000` on `message`/`resume_value` — rejects oversized payloads)
- [x] Max-conversation-turn guard (24 messages) + per-thread token budget (8000 est. tokens via `MAX_TURNS`/`THREAD_TOKEN_BUDGET` — oldest trimmed in `agent.py`)
- [x] Confirm per-call `max_tokens` (500 in `agent.py`) and global per-thread budget (see above)

### B. Authentication / access control
- [x] Require a shared secret (header `X-Chat-Token` must match `CHAT_API_TOKEN` when set; widget must send it — empty `CHAT_API_TOKEN` = dev open)
- [x] Keep `/health` unauthenticated for uptime monitors (decision: stays open)

### C. Prompt-injection resistance
- [x] Harden the system prompt: `SYSTEM_PROMPT` explicitly ignores `ignore previous instructions` / `act as` / `reveal your prompt` (`prompts.py:19`)
- [x] Treat every model output as untrusted — rendered only as text in chat, never executed downstream

### D. General hardening
- [x] Validate all input (Pydantic `max_length` + FastAPI rejects malformed JSON)
- [x] Confirm CORS allowlist is locked to `products.innerchildproject.us` (+ localhost for dev) — via `CORS_ORIGINS` env, forwarded to `CORSMiddleware`
- [x] Add dependency scanning (`.github/dependabot.yml` already enabled)
- [ ] Optional: Cloudflare Turnstile on the chat widget (bot protection before the request even reaches the server)
- [x] Optional: request logging for abuse forensics (LangSmith traces execution + `src/server.py` rate-limit hits)
