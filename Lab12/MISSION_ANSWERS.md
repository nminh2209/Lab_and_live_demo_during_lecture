# Day 12 Lab — Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. **Hardcoded API key** (`OPENAI_API_KEY = "sk-hardcoded-..."`) — secrets in source code leak when pushed to Git.
2. **Hardcoded database credentials** (`password123` in `DATABASE_URL`) — same risk as API keys.
3. **`print()` for logging** — unstructured logs are hard to search and may leak secrets.
4. **No health check endpoint** — the platform cannot detect crashes or restart the service.
5. **Fixed port and `host="localhost"`** — cloud platforms inject `PORT` and require `0.0.0.0`.
6. **`reload=True` in production** — debug reload is unsafe and wasteful in production.
7. **No graceful shutdown** — in-flight requests may be dropped on deploy/restart.
8. **No config management** — `DEBUG`, `MAX_TOKENS` are not environment-driven.

### Exercise 1.3: Comparison table

| Feature | Basic (develop) | Advanced (production) | Why Important? |
|---------|-----------------|----------------------|----------------|
| Config | Hardcoded in code | `os.getenv` / Settings | Change per environment without code changes; avoid committing secrets |
| Health check | Missing | `GET /health` | Lets Railway/Render/K8s know when to restart or route traffic |
| Logging | `print()` | JSON structured logs | Easy to parse in Datadog/Loki; supports alerting |
| Shutdown | Abrupt exit | Lifespan + SIGTERM | Finishes active requests during rolling deploys |
| Host binding | `localhost` | `0.0.0.0` | Required inside Docker/cloud so external traffic can reach the app |
| Port | Fixed `8000` | `PORT` env var | Cloud platforms assign ports dynamically |
| CORS | None | Configured origins | Reduces browser-based abuse from unknown frontends |
| Readiness | None | `GET /ready` | Load balancers only send traffic when dependencies are ready |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image:** `python:3.11-slim` — lightweight OS + Python runtime.
2. **Working directory:** `/app` — application code lives here inside the container.
3. **Copy requirements first:** Docker layer caching — dependencies rebuild only when `requirements.txt` changes.
4. **CMD vs ENTRYPOINT:** `CMD` is the default command and can be overridden at `docker run`; `ENTRYPOINT` defines the fixed executable and is harder to override.

### Exercise 2.3: Image size comparison

- **Develop (single-stage):** Larger image because build tools (`gcc`, pip cache) remain in the final layer.
- **Production (multi-stage):** Smaller image — only runtime dependencies copied from the builder stage.
- **Typical difference:** ~50–70% smaller with multi-stage + `slim` base image.
- **Target:** Final image under 500 MB for this lab.

### Exercise 2.4: Architecture diagram

```
Client → Nginx (:80) → Agent (:8000, scaled) → Redis (:6379)
```

- **Nginx:** round-robin load balancing across agent replicas.
- **Agent:** stateless FastAPI instances; conversation/rate/cost state in Redis.
- **Redis:** shared session, rate-limit, and budget storage.

---

## Part 3: Cloud Deployment

### Exercise 3.1: Render deployment

- **Config file:** `render.yaml` at repo root — Docker web service + Redis, `rootDir: 06-lab-complete`.
- **Required env vars:** `AGENT_API_KEY` (auto-generated), `REDIS_URL` (linked from Redis service), optional `OPENAI_API_KEY`.
- **Deploy flow:** Push to GitHub → Render Dashboard → **New +** → **Blueprint** → connect repo → Apply.

### Exercise 3.2: Render configuration notes

| Aspect | Render (`render.yaml`) |
|--------|-------------------------|
| Config format | YAML Blueprint |
| Health check | `healthCheckPath: /health` |
| Secrets | Dashboard `sync: false` or `generateValue: true` |
| Redis | `fromService` reference in Blueprint |

### Exercise 3.3: GCP Cloud Run (optional)

- `cloudbuild.yaml` builds the image on push.
- `service.yaml` defines Cloud Run service, env, and scaling.
- CI/CD: Git push → Cloud Build → deploy new revision with zero-downtime traffic shift.

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

- Key checked in `verify_api_key` dependency via `X-API-Key` header.
- Missing/invalid key → **401 Unauthorized**.
- Rotate key by updating `AGENT_API_KEY` in env and redeploying; no code change needed.

### Exercise 4.2: JWT authentication

- `POST /auth/token` with username/password returns a signed JWT.
- Protected routes use `Authorization: Bearer <token>`.
- Token payload includes `sub` (user) and `role`; expiry enforced on decode.
- Demo users: `student/demo123`, `teacher/teach456` (admin gets higher rate limit).

### Exercise 4.3: Rate limiting

- **Algorithm:** sliding window counter (timestamps in a 60-second window).
- **Default limit:** 10 requests/minute per user (lab final project).
- **Admin bypass:** in `04-api-gateway/production`, admin uses `rate_limiter_admin` (100 req/min).

### Exercise 4.4: Cost guard implementation

- Track estimated token cost per user per calendar month in Redis.
- Pricing reference: GPT-4o-mini input $0.15/1M, output $0.60/1M tokens.
- Before LLM call: `check_budget(user_id)` — raises **402** when `MONTHLY_BUDGET_USD` (default $10) is exceeded.
- After LLM call: `record_usage()` persists updated spend.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health and readiness

- **`/health` (liveness):** process is up; returns `degraded` if Redis configured but unreachable.
- **`/ready` (readiness):** returns 503 during startup/shutdown or when Redis is required but down.

### Exercise 5.2: Graceful shutdown

- `SIGTERM`/`SIGINT` handlers log the signal.
- Lifespan shutdown waits up to 30s for in-flight requests.
- Uvicorn `timeout_graceful_shutdown=30`.

### Exercise 5.3: Stateless design

- Conversation history, rate limits, and monthly cost stored in **Redis**, not process memory.
- Any agent replica can serve the same `user_id` without losing context.

### Exercise 5.4: Load balanced stack

```bash
cd 06-lab-complete
docker compose up --scale agent=3
curl http://localhost/health
```

### Exercise 5.5: Stateless test

```bash
# Request 1 — creates history
curl -X POST http://localhost/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice","question":"Hello"}'

# Request 2 — recalls prior message (mock or OpenAI with history)
curl -X POST http://localhost/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice","question":"What did I just say?"}'
```

---

## Part 6: Final Project Notes

- **LLM:** Set `OPENAI_API_KEY` in `.env.local` or cloud dashboard to use OpenAI; otherwise mock LLM runs offline.
- **Validation:** `cd 06-lab-complete && python check_production_ready.py`
- **Stack:** agent + redis + nginx (`docker compose up --scale agent=3`)
