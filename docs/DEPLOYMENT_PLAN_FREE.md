# Deployment Plan — Free Tier (Hackathon)

> Target: Hackathon submission by Jun 15. Demo Day Jul 2–3.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    PRODUCTION                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐   │
│  │  Vercel   │────▶│  Vercel  │────▶│ Mantle   │   │
│  │  (Web)    │     │  Edge    │     │ Sepolia  │   │
│  │  Free     │     │  Functions│    │ (chain)  │   │
│  └──────────┘     └──────────┘     └──────────┘   │
│                          │                          │
│                   ┌──────┴──────┐                   │
│                   │   Cloudflare │                  │
│                   │   Worker     │                  │
│                   │   (proxy)    │                  │
│                   └──────┬──────┘                   │
│                          │                          │
│                   ┌──────▼──────┐                   │
│                   │   Bybit     │                  │
│                   │   Testnet   │                  │
│                   └─────────────┘                   │
│                                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                   LOCAL DEV                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  docker compose up -d                               │
│  ├── postgres (5432)                                │
│  ├── redis (6379)                                   │
│  ├── api (8000)                                     │
│  ├── boule (8002)                                   │
│  ├── areopagus (8003)                               │
│  ├── strategos (8004)                               │
│  └── ... (all services)                             │
│                                                     │
│  pnpm --filter @athean/web dev                      │
│  └── localhost:3000                                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Free Tier Stack

| Component | Provider | Free Tier | Notes |
|-----------|----------|-----------|-------|
| **Web (Next.js)** | Vercel | 100GB bandwidth, unlimited sites | Already configured (`vercel.json`) |
| **API Gateway** | Render.com | 750 hrs/mo, spins down after inactivity | FastAPI, cold start ~30s |
| **PostgreSQL** | Neon | 0.5GB storage, 24/7 | Serverless, auto-suspend |
| **Redis** | Upstash | 10K cmds/day, 256MB | Serverless, pay-per-request |
| **Bybit Proxy** | Cloudflare Workers | 100K req/day | Route around geo-block |
| **Monitoring** | Vercel Analytics | Included | Already in package.json |
| **Domain** | Vercel | `*.vercel.app` | Free subdomain |

**Total cost: $0/month**

---

## Step 1: Deploy Web to Vercel

Already ready. Just connect GitHub repo:

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy from project root
vercel --cwd apps/web

# Or connect via Vercel dashboard:
# 1. Import GitHub repo
# 2. Root directory: apps/web
# 3. Framework: Next.js
# 4. Build command: pnpm turbo run build --filter=@athean/web...
# 5. Output: .next (default)
```

**Environment variables to set in Vercel dashboard:**
```env
NEXT_PUBLIC_PROOF_OF_RESTRAINT_ADDRESS=0xaCB12755134900196F8eE4Ae5223e6955B8Aa7Af
NEXT_PUBLIC_VISITOR_WITNESS_ADDRESS=0xDf7939Da6366D8086E2E70cDB3d125eAdeBE7626
NEXT_PUBLIC_MANTLE_EXPLORER_URL=https://explorer.sepolia.mantle.xyz
```

---

## Step 2: Deploy API to Render.com

### 2.1 Create `render.yaml` at project root:

```yaml
services:
  - type: web
    name: athean-api
    runtime: python
    plan: free
    buildCommand: |
      cd services/strategos && uv sync
      cd services/boule && uv sync
      cd services/apollo && uv sync
      cd services/areopagus && uv sync
      cd packages/athean-core && uv sync
      cd apps/api && uv sync
    startCommand: cd apps/api && uv run uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: REDIS_URL
        sync: false
      - key: RPC_URL
        value: https://rpc.sepolia.mantle.xyz
      - key: CHAIN_ID
        value: "5003"
```

### 2.2 Database: Neon (free PostgreSQL)

1. Sign up at https://neon.tech
2. Create project → copy connection string
3. Set as `DATABASE_URL` in Render env vars

### 2.3 Redis: Upstash (free Redis)

1. Sign up at https://upstash.com
2. Create Redis store → copy URL
3. Set as `REDIS_URL` in Render env vars

---

## Step 3: Bybit Proxy (Cloudflare Workers)

Route around geo-block without VPN.

### 3.1 Create `workers/bybit-proxy/index.js`:

```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = `https://api-testnet.bybit.com${url.pathname}${url.search}`;

    const proxyReq = new Request(target, {
      method: request.method,
      headers: request.headers,
      body: request.body,
    });

    const response = await fetch(proxyReq);
    const proxyRes = new Response(response.body, response);

    // CORS headers
    proxyRes.headers.set('Access-Control-Allow-Origin', '*');
    proxyRes.headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    proxyRes.headers.set('Access-Control-Allow-Headers', '*');

    return proxyRes;
  }
};
```

### 3.2 Deploy:

```bash
# Install wrangler
npm i -g wrangler

# Login
wrangler login

# Create worker
wrangler init bybit-proxy

# Deploy
wrangler deploy
```

### 3.3 Use proxy in Strategos:

```env
BYBIT_BASE_URL=https://bybit-proxy.your-subdomain.workers.dev
```

---

## Step 4: Paper Trade (48h Evidence)

Run locally with Bybit proxy:

```bash
# Set env vars
export BYBIT_API_KEY=ySelf7mja3wIqpuXJg
export BYBIT_API_SECRET=YmjIi2HKCmStLXnbzrMRp2z7tASoN6AJHMJR
export BYBIT_TESTNET=true
export BYBIT_BASE_URL=https://bybit-proxy.your-subdomain.workers.dev
export EXECUTION_MODE=bybit_paper
export BOULE_LLM_PROVIDER=gemini
export GEMINI_API_KEY=...

# Run paper trade (cycles every 5 min)
cd services/strategos
uv run python ../../scripts/bybit_paper_trade.py \
  --symbols BTCUSDT ETHUSDT \
  --interval 300 \
  --max-cycles 576  # 48 hours
```

Output: `artifacts/bybit_paper_*.json`

---

## Step 5: Demo Video

Record locally:

```bash
# Terminal 1: Web dashboard
pnpm --filter @athean/web dev

# Terminal 2: Paper trade
cd services/strategos && uv run python ../../scripts/bybit_paper_trade.py --max-cycles 3

# Terminal 3: Chain watcher
watch -n5 'cast call 0xaCB12755134900196F8eE4Ae5223e6955B8Aa7Af "getRestrainedCount()(uint256)" --rpc-url https://rpc.sepolia.mantle.xyz'
```

**Recording script:**
```bash
# macOS screen recording
Cmd + Shift + 5 → Record Selected Portion
# Or use OBS Studio (free)
```

---

## Step 6: X Submission Thread

Draft in `docs/SUBMISSION_THREAD.md` (see below).

---

## Quick Start (5 minutes)

```bash
# 1. Deploy web to Vercel
vercel --cwd apps/web

# 2. Set up Neon + Upstash (free databases)
#    → Copy connection strings

# 3. Deploy API to Render
#    → Connect GitHub repo, set env vars

# 4. Deploy Bybit proxy to Cloudflare Workers
wrangler deploy

# 5. Run paper trade locally
cd services/strategos && uv run python ../../scripts/bybit_paper_trade.py --max-cycles 10
```

---

## Cost Summary

| Item | Cost |
|------|------|
| Vercel (web) | $0 |
| Render (API) | $0 |
| Neon (PostgreSQL) | $0 |
| Upstash (Redis) | $0 |
| Cloudflare Workers (proxy) | $0 |
| **Total** | **$0** |

---

## Limitations (Free Tier)

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Render spins down after 15min inactivity | API cold start ~30s | Acceptable for demo |
| Neon 0.5GB storage | Enough for hackathon | Upgrade if needed |
| Upstash 10K cmds/day | Paper trade uses ~1K/day | Fine for demo |
| Vercel 100GB bandwidth | Dashboard is lightweight | Fine for demo |
| Cloudflare Workers 100K req/day | Paper trade uses ~288/day | Fine for demo |

---

## Security Notes

- **NEVER commit API keys** to git
- Use Vercel/Render env var dashboards for secrets
- Rotate Bybit keys after hackathon
- Bybit testnet keys are low-risk (testnet only)
