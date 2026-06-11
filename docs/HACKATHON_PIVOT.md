# Mantle Turing Test Hackathon 2026 — Pivot Strategy

> Track target: **AI Trading & Strategy** (Sponsored by BGA & Bybit)
> Deadline: Phase 2 submission Jun 15 · Demo Day Jul 2–3 · Winners Jul 10
> Prize: $8,500 Track First Prize + $9,000 Grand Champion + $1,000 Finalist pool

---

## 1. Hackathon Overview

| Item | Detail |
|------|--------|
| Organiser | Mantle + DoraHacks |
| Total pool | $120,000 cash + $103,000 API credits = **$223K+** |
| Phase 1 (ClawHack) | Apr 15–30, 2026 — $20K — AI agents on RealClaw/OpenClaw, judged on volume & ROI |
| Phase 2 (AI Awakening) | May 1–Jun 15, 2026 — $100K — 6 tracks, Human vs. AI mechanism |
| Demo Day | Jul 2–3, 2026 (live-streamed globally) |
| Winners announced | Jul 10, 2026 |
| Blockchain required | **Mantle** (mainnet or Mantle Sepolia testnet) |
| Submission channel | X (Twitter) thread with `#MantleAIHackathon` |

### Prize Breakdown (Phase 2)

| Prize | Amount |
|-------|--------|
| Grand Champion | $9,000 |
| Track First Prize × 6 | $8,500 each = $51,000 |
| Community Voting × 2 | $8,500 each = $17,000 |
| Best UI/UX | $3,000 |
| Finalist Deployment × 20 | $1,000 each = $20,000 |

### Available API Credits (apply separately)

| Provider | Value | Use |
|----------|-------|-----|
| Elfa AI | $36,000 | Inference API |
| Surf AI | $30,000 | Compute |
| Orbit AI | $30,000 | Infrastructure |
| Nansen | $7,000 | On-chain data |
| AltLLM | $7,000 | LLM chat/framework |

---

## 2. Target Track — AI Trading & Strategy

**Official description:**
> "AI quant bots and macro-driven smart contracts, with Python and Solidity templates and Bybit API support."
> — Sponsored by BGA (Blockchain for Good Alliance) & Bybit

### What judges expect to see

Synthesised from judging panel composition (Nansen, Allora Network, Caladan, Hashed, Virtuals Protocol) and Phase 1 evaluation criteria:

| Dimension | What it means for us |
|-----------|---------------------|
| **AI decision quality** | Multi-agent council producing structured, auditable trade theses |
| **On-chain transparency** | Every agent decision recorded on Mantle — not just trades, but *restraint* |
| **Strategy sophistication** | Kelly sizing, drawdown guards, signal compositing — not simple rule-bots |
| **Bybit integration** | Live or paper execution via Bybit REST/WebSocket API |
| **Python + Solidity stack** | Python services for AI logic + Solidity for on-chain attestation |
| **Performance metrics** | ROI, Sharpe, Brier score vs. baseline — quantified, not claimed |
| **ERC-8004 identity** | Each agent has an on-chain NFT passport tracking its decisions |

---

## 3. Alignment Analysis — What We Already Have

Athean is architecturally near-perfect for this track. Most of the hard work is already done.

### Strong alignments ✅

| Hackathon requirement | Existing Athean component | Notes |
|----------------------|--------------------------|-------|
| AI quant bots | `services/boule` — 11-agent Claude council | Produces structured Thesis JSON per trade |
| Multi-agent debate | Boule council (Aristotle, Pythagoras, Heraclitus…) | Adversarial dissent built-in |
| Python AI services | All 13 services in Python 3.12 + uv | Already structured as microservices |
| Solidity smart contracts | `contracts/` — Foundry project | PantheonConstitution, ProofOfRestraint deployed |
| ERC-8004 agent passports | `services/parthenon` + `docs/ERC8004_INTEGRATION.md` | **Direct alignment — rare differentiator** |
| On-chain decision recording | `ProofOfRestraint.sol` — anchors every verdict | Both approvals AND restraints on-chain |
| Risk management | `services/areopagus` — Kelly, drawdown, correlation | Hard gate before any execution |
| Signal scoring | `services/apollo` — edge/liquidity/sentiment | Composited into typed Pydantic signals |
| Trade execution | `services/strategos` — paper/live/auto modes | Already abstracted via `EXECUTION_MODE` |
| Backtesting | `services/elysium` — 200-market backtest | Brier 0.149 vs. human 0.126 baseline |
| Performance scoring | `services/ostrakon` — Brier + Sharpe leaderboard | Quantified, auditable metrics |
| Web dashboard | `apps/web` — Next.js 14, live data, chain ticker | Ready for demo-day presentation |

### Gaps to fix 🔧

| Gap | Current state | Required change |
|----|--------------|-----------------|
| **Blockchain** | Arc Testnet (Circle) | Migrate to **Mantle Sepolia** testnet |
| **CEX execution** | Polymarket CLOB only | Add **Bybit API** (REST + WS) to Strategos |
| **Market scope** | Prediction markets only | Extend to spot/perp markets via Bybit |
| **RPC/chain config** | Arc RPC hardcoded | Make chain configurable; default to Mantle |
| **Brand framing** | "Athean Trades on Arc" | "AI Trading Council on Mantle + Bybit" |

---

## 4. Migration Plan: Arc → Mantle

### 4.1 Chain configuration

Mantle Sepolia testnet:
- RPC: `https://rpc.sepolia.mantle.xyz`
- Chain ID: `5003`
- Explorer: `https://explorer.sepolia.mantle.xyz`
- Native token: MNT (gas)
- Faucet: `https://faucet.testnet.mantle.xyz`

Mantle Mainnet (for Demo Day):
- RPC: `https://rpc.mantle.xyz`
- Chain ID: `5000`
- Explorer: `https://explorer.mantle.xyz`

### 4.2 Contract changes

No logic changes needed. The contracts (`PantheonConstitution.sol`, `ProofOfRestraint.sol`, ERC-8004 registry) are chain-agnostic. Steps:

1. Update `foundry.toml` — add `[rpc_endpoints]` for `mantle_testnet` and `mantle_mainnet`
2. Update `contracts/.env.example` — `RPC_URL=https://rpc.sepolia.mantle.xyz`, `CHAIN_ID=5003`
3. Run `forge script DeployAthean --rpc-url mantle_testnet --broadcast`
4. Update `.env.example` at root with new contract addresses
5. Update `apps/web/lib/arc-client.ts` → rename to `mantle-client.ts`, point to Mantle RPC

### 4.3 Environment variable changes

```env
# FROM
RPC_URL=https://rpc.arc.circle.com
CHAIN_ID=480

# TO
RPC_URL=https://rpc.sepolia.mantle.xyz
CHAIN_ID=5003

# New
MANTLE_EXPLORER=https://explorer.sepolia.mantle.xyz
MNT_TOKEN_ADDRESS=0x...   # native gas token on Mantle
```

---

## 5. Bybit API Integration

### 5.1 What to add

Bybit V5 API supports:
- **Spot trading** — buy/sell crypto pairs
- **USDT Perpetuals** — leveraged directional bets (matches prediction market logic)
- **WebSocket streams** — real-time price, orderbook, fills
- **Paper trading** — Bybit testnet (`https://api-testnet.bybit.com`)

### 5.2 Integration point: `services/strategos`

Strategos already abstracts execution behind an `ExecutionMode` enum. Add a new backend:

```
services/strategos/src/strategos/
  backends/
    polymarket.py   ← existing
    bybit.py        ← NEW — Bybit V5 REST + WebSocket
  execution_mode.py ← add BYBIT_PAPER, BYBIT_LIVE modes
```

Bybit credentials to add to `.env.example`:
```env
BYBIT_API_KEY=
BYBIT_API_SECRET=
BYBIT_TESTNET=true          # false for mainnet
BYBIT_BASE_URL=https://api-testnet.bybit.com
```

### 5.3 Mapping Athean concepts → Bybit

| Athean | Bybit equivalent |
|--------|-----------------|
| Signal (probability 0–1) | Position size via Kelly criterion → order qty |
| Thesis verdict APPROVE | Market/limit order via `/v5/order/create` |
| Thesis verdict REJECT | No order (ProofOfRestraint anchored on-chain) |
| Argos monitoring | WebSocket `/v5/private/execution` stream |
| Ostrakon scoring | ROI from fills + Sharpe over rolling window |

### 5.4 Bybit Python SDK

```bash
# In services/strategos/pyproject.toml, add:
"pybit>=5.7"
```

---

## 6. Submission Requirements Checklist

The official submission requires posting a thread on X with `#MantleAIHackathon` containing:

- [ ] **Project pitch** — 1-paragraph description of the AI council trading system
- [ ] **Demo video** — screen recording of council debate → verdict → on-chain proof
- [ ] **GitHub repository** — public repo with full source + README
- [ ] **Mantle contract address** — deployed `ProofOfRestraint` on Mantle testnet/mainnet

Additional strong-signal items (not required but heavily weighted):

- [ ] **ERC-8004 passport addresses** — each of the 11 agents has an on-chain NFT identity
- [ ] **Live Brier/Sharpe metrics** — quantified performance vs. random baseline
- [ ] **Bybit paper trade log** — CSV or on-chain record of past 48h decisions
- [ ] **Architecture diagram** — shows full pipeline from signal → debate → execution → attestation

---

## 7. Narrative Reframe for Judges

The project is fundamentally a **Human vs. AI** benchmark — exactly what the hackathon's "Human vs. AI mechanism" is designed to showcase. Our framing:

> **"Athean is an eleven-agent AI council that debates every trade before execution on Mantle. Every approval — and every act of restraint — is anchored on-chain via ERC-8004 agent passports and a ProofOfRestraint contract. In a 200-market backtest, the council closes 80% of the LLM-vs-human Brier score gap. The system executes via Bybit API with Kelly-sized positions and a hard Areopagus risk gate."**

This directly answers the hackathon's core question: *can an AI system make better trading decisions than a human, and can we prove it on-chain?*

---

## 8. Pivot Priority Order

Execute in this sequence to reach a submittable state:

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | Deploy contracts to Mantle Sepolia | 2h | Required for submission |
| 2 | Update RPC/chain config in all services + web | 3h | Required for demo |
| 3 | Add `bybit.py` backend in Strategos | 1 day | Track differentiator |
| 4 | Wire Bybit paper trades to Ostrakon scorer | 4h | Metric for judges |
| 5 | Update web dashboard — show Mantle chain, Bybit fills | 4h | Demo day presentation |
| 6 | Record 48h of paper trades on Bybit testnet | 24h running | Live evidence |
| 7 | Write X submission thread + demo video | 3h | Submission deadline |
| 8 | Apply for Elfa AI + Nansen API credits | 1h | Free $43K in credits |

**Total estimated effort: ~3–4 days of focused work.**

---

## 9. Key Reference Links

- [Hackathon main page](https://dorahacks.io/hackathon/mantleturingtesthackathon2026/detail)
- [Mantle DevHub](https://devhub.mantle.xyz/)
- [Mantle Sepolia Faucet](https://faucet.testnet.mantle.xyz)
- [Mantle Sepolia Explorer](https://explorer.sepolia.mantle.xyz)
- [Bybit V5 API docs](https://bybit-exchange.github.io/docs/v5/intro)
- [pybit Python SDK](https://github.com/bybit-exchange/pybit)
- [ERC-8004 spec](https://eips.ethereum.org/EIPS/eip-8004) *(already implemented in Parthenon)*
- [OpenClaw framework](https://github.com/byrealclaw/openclaw) *(Phase 1 reference)*
- [API Credits application form](https://devhub.mantle.xyz/) *(apply for Elfa/Nansen/Surf/Orbit)*

---

## 10. What Makes Us Win

Compared to typical hackathon submissions that are demos-only or single-agent bots, Athean has:

1. **Full production architecture** — 13 services, not a script
2. **Adversarial multi-agent debate** — not one LLM, but 11 agents with structured disagreement
3. **Proof of Restraint** — unique primitive: *no-trade* decisions are also on-chain proof
4. **ERC-8004 already live** — most teams won't know this standard exists
5. **Quantified backtesting** — Brier 0.149 vs. human 0.126 on 200 markets = numbers judges can cite
6. **Risk gate (Areopagus)** — Kelly criterion + correlation-aware sizing = institutional-grade

The only gap is the Mantle + Bybit integration. Everything else is already built.
