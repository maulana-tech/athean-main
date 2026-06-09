# AGENTS.md — OpenCode Agent Instructions

## Project

Athean Trades: AI prediction market trading system. Eleven-agent council debates every trade before Polymarket CLOB execution. On-chain restraint receipts on Arc Testnet.

## Monorepo

- **JS**: pnpm workspaces + Turborepo. Apps under `apps/`, shared packages under `packages/`.
- **Python**: Each service under `services/` has its own `uv` env + `pyproject.toml`. Never mix pip with uv.
- **Contracts**: Foundry under `contracts/`. Solidity 0.8.24, `cancun` EVM, OpenZeppelin + forge-std.
- `.npmrc` sets `node-linker=hoisted` — do not change.

## Task Runners

`just` is preferred over `make` (cross-platform, same targets). Both work.

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
just halmos           # Halmos symbolic checks
just mutmut           # mutation tests on financial modules
```

## Quick Commands

```bash
# Install everything
pnpm install
uv sync --all-packages          # or: make install

# Dev servers
pnpm dev                        # all apps in parallel via turbo
pnpm --filter @athean/web dev   # just the Next.js site → localhost:3000

# Full verification suite
make test                       # syntax → forge test → python integration
python tests/bench.py           # correctness + microbenchmarks
```

## Testing

```bash
# Python — single service (preferred)
cd services/boule && uv run pytest -q
cd services/areopagus && uv run pytest -q

# Python — single test file
cd services/boule && uv run pytest tests/test_orchestrator.py -q

# Python — integration (from repo root, needs PYTHONPATH)
PYTHONPATH=packages/athean-core/src:services/areopagus/src:services/apollo/src:services/boule/src:services/argos/src:services/strategos/src:services/parthenon/src:services/ostrakon/src:services/moirai/src:services/underworld/src:apps/api/src \
  python -m pytest tests/test_pipeline_integration.py -q

# Python — syntax check all sources
python tests/_syntax_check.py

# Solidity
forge test --root contracts
forge test --root contracts -vv  # verbose (CI default)

# Halmos symbolic verification
cd contracts && uvx halmos --solver-timeout-assertion 30000
```

**CI order**: syntax check → per-service pytest (matrix) → integration → forge test → halmos → slither.

## Linting & Formatting

```bash
uvx ruff check .                # Python lint
uvx ruff check --fix . && uvx ruff format .  # auto-fix + format
pnpm lint                       # JS/TS lint via turbo
cd contracts && forge fmt --check  # Solidity formatting

# Full lint (what CI runs)
uvx ruff check . && pnpm lint && cd contracts && forge fmt --check src test script
```

Pre-commit hooks run ruff, forge fmt, gitleaks, and an agent-prompts drift check. Install with `pre-commit install`.

## Web App Verification

```bash
cd apps/web && pnpm type-check && pnpm build   # typecheck + build
```

## Architecture (Data Flow)

```
Pythia (data) → Apollo (signals) → Boule (council debate) → Areopagus (risk gate) → Strategos (execution)
                                                                                 → ProofOfRestraint (on-chain)
Argos (monitor) → Ostrakon (scoring) → Underworld (post-mortems) → Olympus (governance)
Parthenon (IPFS/Irys archive)
Moirai (lifecycle enforcement)
Elysium (backtesting)
```

## Key Invariants

- **No trade without Areopagus approval** — never bypass the risk gate.
- **No direct IPFS calls** — route through Parthenon.
- **No hardcoded keys** — secrets live in `.env` / SOPS + age.
- **Never modify `PantheonConstitution.sol`** — immutable by design.
- Agent prompts in `services/boule/src/boule/prompts/*.md` must stay in sync with `apps/web/lib/agent-prompts.ts` (enforced by `tests/check_agent_prompts.py`).
- Network calls and LLM calls in tests are forbidden — mock at the HTTP layer.

## Python Conventions

- Python 3.12. `asyncio_mode = "auto"` in all pytest configs.
- Pydantic v2 models for all typed data (signals, theses, traces).
- structlog for logging. tenacity for retries.
- Each service is independently deployable — no shared pip blast radius.
- `athean-core` package at `packages/athean-core/` is the shared schema/util library.

## LLM Configuration

Single env var switches providers: `BOULE_LLM_PROVIDER=anthropic|gemini|openai|groq|together|deepseek|xai|openai_compat|ollama|lm_studio`.

Fallback chain: `BOULE_LLM_FALLBACK_CHAIN=anthropic,gemini:gemini-3.5-flash,gemini:gemini-2.5-flash-lite`. Providers missing their key env are silently dropped at boot.

## Ports

| Service | Port |
|---------|------|
| api (FastAPI) | 8000 |
| web (Next.js) | 3000 |
| boule | 8002 |
| areopagus | 8003 |
| strategos | 8004 |
| grafana | 3001 |
| prometheus | 9090 |

Full port map: `CLAUDE.md`.

## Gotchas

- `docker compose up -d` starts Postgres, Redis, IPFS, all services, observability, and backups. Services depend on Redis health — wait for it.
- `make install` (or `just install`) runs `uv sync` per service in a loop — slow on first run.
- Forge tests live in `contracts/test/` — there are 65+ tests across 20 suites plus 12 Halmos symbolic checks.
- The `tests/` directory at repo root contains cross-service benchmarks and integration tests, not per-service unit tests.
- Agent prompts are Markdown files that get bundled into the web app. Edit the `.md` files, not the TS bundle.
- Secrets: `.env.example` shows required vars. Never commit `.env`. SOPS + age for encrypted secrets.
- Contracts have their own `.env.example` under `contracts/`.
- `uvx` runs one-off tools without installing globally (e.g. `uvx ruff check .`, `uvx halmos`).

## Docs Index

Key design docs for understanding the system (not exhaustive):

- `docs/ARCHITECTURE.md` — system design and data flow
- `docs/AGENTS.md` — agent roster, roles, debate structure
- `docs/CONSTITUTION.md` — immutable system rules
- `docs/SIGNAL_SPEC.md` — signal schema
- `docs/THESIS_SCHEMA.md` — thesis structure
- `docs/RISK_POLICY.md` — position limits and gates
- `docs/TRACE_FORMAT.md` — trace event schema
- `docs/MOIRAI_LAWS.md` — lifecycle rules
- `docs/EDGE_SOURCES.md` — catalogued edge sources with falsification criteria
