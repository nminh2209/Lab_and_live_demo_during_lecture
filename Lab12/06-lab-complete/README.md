# Lab 12 — Complete Production Agent

Full production agent combining all Day 12 concepts.

## Checklist

- [x] Multi-stage Dockerfile (< 500 MB)
- [x] docker-compose.yml (agent + redis + nginx)
- [x] API Key authentication (`app/auth.py`)
- [x] Redis rate limiting (`app/rate_limiter.py`)
- [x] Monthly cost guard — $10/month (`app/cost_guard.py`)
- [x] Conversation history in Redis (stateless)
- [x] Health + readiness probes
- [x] Graceful shutdown (SIGTERM)
- [x] OpenAI when `OPENAI_API_KEY` is set; mock otherwise
- [x] `render.yaml` (Render Blueprint)

## Structure

```
06-lab-complete/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── rate_limiter.py
│   ├── cost_guard.py
│   ├── session.py
│   └── redis_client.py
├── utils/
│   ├── mock_llm.py
│   └── llm.py
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
└── check_production_ready.py
```

## Run locally (Python)

```bash
cd 06-lab-complete
pip install -r requirements.txt
cp .env.example .env.local
# Optional: set OPENAI_API_KEY=sk-... in .env.local
export $(grep -v '^#' .env.local | xargs)   # Linux/macOS
python -m app.main
```

## Run with Docker Compose

```bash
cp .env.example .env.local
# Optional: add OPENAI_API_KEY to .env.local, then:
docker compose up --build --scale agent=3
```

```bash
curl http://localhost/health
curl -X POST http://localhost/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo","question":"What is Docker?"}'
```

## OpenAI

Paste your key into `.env.local` or cloud env:

```
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini
```

Without the key, the agent uses the mock LLM (works offline).

## Production readiness

```bash
python check_production_ready.py
```

## Deploy

See [DEPLOYMENT.md](../DEPLOYMENT.md) and [RENDER.md](RENDER.md).
