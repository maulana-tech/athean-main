# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AI prediction market trading system. An eleven-agent council of Greek-god-named agents debates trades before execution on Polymarket CLOB. All decisions — including restraint — are traced, archived on-chain, and scored.

## Monorepo

pnpm workspaces + Turborepo for JS/TS. Python services use uv. Never mix pip with uv.

`just` is the preferred task runner (over `make`):

```bash
just install          # pnpm install + uv sync --all-packages
just dev              # turbo run dev --parallel
just test             # pnpm test + forge test
just test-service <svc>  # cd services/<svc> && uv run pytest -q
just lint             # ruff check + pnpm lint + forge fmt --check
just fmt              # ruff check --fix + ruff format
just up / just down   # docker compose up/down
just logs <service>   # docker compose logs -f <service>
just migrate          # alembic upgrade head (in apps/api)
just migrate-revision "msg"  # create a new alembic revision
just halmos           # Halmos symbolic checks for Solidity invariants
just mutmut           # mutation tests on financial modules
```

Equivalent Makefile targets exist for everything above (`make install`, `make test`, etc.).

## Python Services

Each service under `services/` and `apps/api/` uses uv:

```bash
cd services/boule && uv run pytest          # run all tests for a service
cd services/boule && uv run pytest tests/test_debate.py::test_quorum -xvs  # single test
cd services/apollo && uv run python -m apollo.cli
```

Solidity:

```bash
forge test --root contracts                           # all contract tests
forge test --root contracts --match-test test_pause  # single test
```

## Architecture

Data flows in one direction through the pipeline:

```
Pythia (data oracle) → Apollo (signal scoring) → Boule (multi-agent debate)
  → Areopagus (risk gate) → Strategos (execution) → Argos (position monitor)
  → Ostrakon (scoring) / Parthenon (archive) / Elysium (backtest)
```

**Boule** runs the council: 11 Claude-named agents each produce a `Thesis`, the council votes, Boule emits a `Verdict`. Supported LLM providers: `anthropic`, `gemini`, `openai`, `openrouter`, `groq`, `together`, `deepseek`, `xai`, `ollama`, `lm_studio`, `openai_compat` — set via `BOULE_LLM_PROVIDER`.

**Areopagus** is the mandatory risk gate — no trade can reach Strategos without its approval. Kelly sizing, drawdown limits, and correlation guards live here.

**Parthenon** is the only allowed path to IPFS/Irys. Other services must never call IPFS directly.

**Moirai** enforces lifecycle rules across services (see `docs/MOIRAI_LAWS.md`).

**Chronos** is the scheduler that triggers market scans and deliberation cycles.

**Underworld** handles post-mortems on failed trades.

**Olympus** governs system goals and adversarial mode.

## Key Conventions

- **Signals**: typed Pydantic models, always validated at source (Pythia) — see `docs/SIGNAL_SPEC.md`
- **Theses**: structured JSON — see `docs/THESIS_SCHEMA.md`
- **Traces**: every Boule run emits a `TraceEvent` per agent step — see `docs/TRACE_FORMAT.md`
- **Risk policy**: position limits live in `docs/RISK_POLICY.md` and are enforced by Areopagus
- **Agent prompts**: Markdown files in `services/boule/src/boule/prompts/`
- **Execution mode**: controlled by `EXECUTION_MODE=paper|live|auto`
- **Shared Python types**: `packages/athean-core` — editable-installed into every service

## Services Port Map

| Service | Port |
|---------|------|
| api (FastAPI) | 8000 |
| apollo | 8001 |
| boule | 8002 |
| areopagus | 8003 |
| strategos | 8004 |
| argos | 8005 |
| ostrakon | 8006 |
| parthenon | 8007 |
| pythia | 8008 |
| elysium | 8009 |
| underworld | 8010 |
| moirai | 8011 |
| olympus | 8012 |
| web (Next.js) | 3000 |

## Environment

Copy `.env.example` before running. Key variables:

- `ANTHROPIC_API_KEY` — Claude API for agent intelligence
- `POLYMARKET_API_KEY` — CLOB trading
- `DATABASE_URL` — PostgreSQL
- `REDIS_URL` — pub/sub and cache
- `IPFS_API_URL` — IPFS node
- `IRYS_KEY` — Irys bundler for permanent storage
- `PRIVATE_KEY` — Mantle wallet (holds MNT for gas)
- `RPC_URL` — Mantle Sepolia: `https://rpc.sepolia.mantle.xyz`
- `CHAIN_ID` — `5003` (Mantle Sepolia) or `5000` (Mantle mainnet)
- `BYBIT_API_KEY` / `BYBIT_API_SECRET` — Bybit V5 CEX execution
- `BOULE_LLM_PROVIDER` — LLM backend for the council
- `EXECUTION_MODE` — `paper` / `live` / `auto`

Contracts have their own `.env.example` under `contracts/`.

## Docs Index

- `docs/ARCHITECTURE.md` — system design
- `docs/AGENTS.md` — agent roster and responsibilities
- `docs/CONSTITUTION.md` — immutable system rules
- `docs/SIGNAL_SPEC.md` — signal schema
- `docs/THESIS_SCHEMA.md` — thesis structure
- `docs/RISK_POLICY.md` — position limits and gates
- `docs/TRACE_FORMAT.md` — trace event schema
- `docs/SETTLEMENT_FLOW.md` — on-chain settlement
- `docs/MOIRAI_LAWS.md` — lifecycle rules
- `docs/PROOF_OF_RESTRAINT.md` — on-chain no-trade recording

## Never Do

- Never bypass Areopagus to submit a trade directly
- Never write to IPFS directly — route through Parthenon
- Never hardcode private keys or API keys
- Never commit `.env` files
- Never modify `PantheonConstitution.sol` after deployment — it is immutable by design
