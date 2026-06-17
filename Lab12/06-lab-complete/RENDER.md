# Deploy to Render — Day 12 Agent

Uses **free** web + Redis tier on Render.

## Prerequisites

- [Render account](https://render.com) (GitHub login)
- This repo pushed to GitHub

## Option A — Blueprint (recommended)

Uses `render.yaml` at the **repository root**.

1. Push this repo to GitHub
2. [Render Dashboard](https://dashboard.render.com) → **New +** → **Blueprint**
3. Connect your GitHub repo
4. Render reads `render.yaml` and creates:
   - `day12-agent` (Docker web service)
   - `day12-redis` (Redis)
5. When prompted, set **`OPENAI_API_KEY`** (optional — mock LLM works without it)
6. Click **Apply** / **Deploy**

After deploy:

1. Open **day12-agent** → **Environment**
2. Copy auto-generated **`AGENT_API_KEY`** (Render generates it)
3. Open **day12-agent** → copy your URL (e.g. `https://day12-agent.onrender.com`)

## Option B — Manual web service

If Blueprint fails:

1. **New +** → **Web Service** → connect repo
2. **Root Directory:** `06-lab-complete`
3. **Runtime:** Docker
4. **Plan:** Free
5. **Health Check Path:** `/health`
6. Add env vars:

| Key | Value |
|-----|--------|
| `ENVIRONMENT` | `production` |
| `AGENT_API_KEY` | generate a strong secret |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `MONTHLY_BUDGET_USD` | `10.0` |
| `REDIS_URL` | from Render Redis instance |
| `OPENAI_API_KEY` | optional |

7. **New +** → **Redis** → free plan → link `REDIS_URL` to web service

## Test

```powershell
$URL = "https://day12-agent.onrender.com"
$KEY = "paste-AGENT_API_KEY-from-dashboard"

curl "$URL/health"
curl "$URL/ready"

curl -X POST "$URL/ask" `
  -H "X-API-Key: $KEY" `
  -H "Content-Type: application/json" `
  -d '{\"user_id\":\"test\",\"question\":\"Hello\"}'
```

## Notes

- **Free tier** web services spin down after ~15 min idle; first request may take 30–60s (cold start).
- Paste `OPENAI_API_KEY` in Render **Environment** when you want real OpenAI instead of mock.
- Update `DEPLOYMENT.md` with your public URL for submission.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails | Confirm **Root Directory** = `06-lab-complete` |
| `/ready` 503 | Check Redis is running and `REDIS_URL` is set |
| Redis DNS error | **Web + Redis must be same region** (both `singapore` in `render.yaml`) |
| Still mock LLM | Set `USE_MOCK_LLM=false` and a valid `OPENAI_API_KEY` (`sk-...`) on **day12-agent**, redeploy |
| OpenAI 502 / Connection error | Keep `LLM_FALLBACK_MOCK=true` so chat still works if OpenAI is unreachable |

### Move Redis to Singapore (cannot change region in place)

Render does **not** let you move Redis Oregon → Singapore. Recreate it:

1. Confirm **day12-agent** → **Settings** → **Region = Singapore** (move web service if needed)
2. **Delete** the Oregon **day12-redis** instance
3. **New +** → **Redis** → name `day12-redis` → **Region: Singapore (Southeast Asia)**
4. **day12-agent** → **Environment** → delete old `REDIS_URL`
5. Add `REDIS_URL` = **Internal** URL from the new Singapore Redis (Connect → Internal)
6. **Manual Deploy** on day12-agent

Or: **Blueprint** → **Sync** after pushing `render.yaml` (both services already specify `region: singapore`).

Internal Redis only works when **web + Redis are in the same region**.
| 401 on `/ask` | Use `AGENT_API_KEY` from Render env in `X-API-Key` header |
| Slow first request | Normal on free tier (cold start) |

```text
Render Dashboard → day12-agent → Logs
```
