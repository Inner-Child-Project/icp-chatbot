# Deploy the ICP Chatbot

The chatbot is a **LangGraph + FastAPI** service. It runs alongside n8n on your server, exposed at `chat.innerchildproject.us` via Cloudflare Tunnel.

## Prerequisites

- Your server already runs n8n (Docker) behind Cloudflare Tunnel
- Docker + docker-compose installed
- `cloudflared` installed (it already is, since n8n uses a tunnel)

---

## Step 1 — Get the code on your server

```bash
git clone git@github.com:Inner-Child-Project/icp-chatbot.git
cd icp-chatbot
cp .env.example .env
# edit .env → paste your real OpenRouter + LangSmith keys
nano .env
```

## Step 2 — Start the service

```bash
docker-compose up -d --build
# verify
curl http://localhost:8100/health
# → {"status":"ok"}
```

## Step 3 — Expose via Cloudflare Tunnel

Add a route for the chatbot on your existing tunnel (or a new one):

```bash
cloudflared tunnel route dns <TUNNEL_NAME> chat.innerchildproject.us
```

Then edit your tunnel config (`~/.cloudflared/config.yml`) to add:

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /home/<user>/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: chat.innerchildproject.us
    service: http://localhost:8100
  - hostname: n8n.innerchildproject.us
    service: http://localhost:5678        # your existing n8n route
  - service: http_status:404
```

Restart the tunnel:

```bash
sudo systemctl restart cloudflared
```

## Step 4 — Point the landing page at it

In the `funnel-machine` repo's Cloudflare build variables, set:

```
PUBLIC_CHAT_API_URL = https://chat.innerchildproject.us
```

(Or the widget already defaults to that URL in `ChatWidget.astro`.)

## Verify end-to-end

```bash
# 1. Health
curl https://chat.innerchildproject.us/health

# 2. Chat
curl -X POST https://chat.innerchildproject.us/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "I run a med spa and need more bookings", "thread_id": "prod-test"}'
# → should return a lead-qualification question
```

Then open `products.innerchildproject.us`, click the 💬 bubble, and talk to the bot.
