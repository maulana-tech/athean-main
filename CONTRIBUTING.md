# Contributing to Athean Trades

Thanks for thinking about contributing. The project is research-grade
on the Python side and immutable-deployed on the Solidity side, so the
contribution rules differ between the two surfaces.

## Quick orientation

- The trading pipeline is Python (`services/*`), one `uv` env per
  service. Never mix `pip` with `uv`.
- The contracts are Solidity 0.8.24, tested with Foundry, symbolically
  verified with Halmos. Production deploys are on Arc Testnet.
- The website is Next.js 14 App Router (`apps/web/`).
- The monorepo is `pnpm` workspaces + Turborepo at the JS layer, with
  uv envs nested inside each Python service.

## Before opening a PR

Run these locally — CI runs the same set.

```bash
# Python
python tests/_syntax_check.py            # 0 errors expected
cd services/<service> && uv run pytest -q

# Contracts
cd contracts && forge fmt --check        # formatting
forge test -vv                           # 57+ tests
python -m halmos --root . \
  --solver-timeout-assertion 30000       # 12 symbolic checks

# Web
cd apps/web && pnpm type-check && pnpm build
```

## What we welcome

- New empirical falsification of edge sources (see `docs/EDGE_SOURCES.md`
  and `scripts/backtest_sources_xml.py`). New ADOPTs require a paired
  Brier-delta test that beats noise on a ≥200-market sample.
- New council agent prompts. Each prompt must:
  - Have a role distinct from the existing 11
  - Define mandate, vote weight, and tone in the same shape as the
    files in `services/boule/src/boule/prompts/`
  - Mirror into `apps/web/lib/agent-prompts.ts` for the `/council`
    viewer (CI compares the two and fails on drift)
- Solidity gas optimisations on contracts marked mutable. The two
  immutable contracts (`PantheonConstitution`, `ProofOfRestraint`)
  cannot be changed — they are deployed.
- New venues for the Polymarket pivot — Kalshi adapter, Manifold
  cross-listing, Odds API sportsbook consensus. See
  `services/pythia/src/pythia/`.
- Documentation improvements, especially `docs/METHODOLOGY` math.
- Test additions. Anywhere. We accept "test-only" PRs.

## What we don't accept

- Speculative features without empirical grounding. "We could add X
  edge source" needs to ship with the backtest that says X moves
  Brier by more than 0.002.
- Breaking changes to the immutable contracts. The Constitution and
  Proof of Restraint are by-design un-upgradeable.
-   LLM-provider lock-in. Athean supports 11 providers; new code
  must work across at least Anthropic, Gemini, OpenAI, and one
  local backend (Ollama / LM Studio).
- New `docs/*.md` files describing features that don't ship in code.
  The repo deliberately keeps documentation:code ratio low. If you
  cannot point at the file that implements the doc, the doc gets
  rejected.
- Mainnet-pointed code without an external audit. Testnet only until
  we have an audit signed off.

## Commit style

- Conventional Commits prefix is preferred (`feat(web):`, `fix(boule):`,
  `chore:`, `docs(methodology):`). Not enforced but appreciated.
- Single-line summary ≤ 72 chars.
- Body wraps at 72 chars. Explain the **why**, not the **what**.
- One logical change per commit. We squash multi-concern PRs.

## Code style

- Python: ruff + black-compatible formatting (the ruff config is in
  `pyproject.toml` at the repo root). 100-char line length.
- Solidity: `forge fmt`. Imports stable-ordered. NatSpec on every
  external function.
- TypeScript: project uses `tsc --noEmit` for type-check and Next's
  built-in lint. No Prettier — Next + ESLint Prettier collisions
  are not worth the import.

## Test discipline

- Every behaviour change ships with a test that fails without the
  change and passes with it. Where this is genuinely impossible
  (rare), the PR description must say so explicitly.
- Network calls in tests are forbidden. Mock at the HTTP layer.
- LLM calls in tests are forbidden. Mock the client.
- Property tests via `hypothesis` are encouraged for math-y code.

## Security

See `SECURITY.md`. Don't open issues for security findings — email
them per the policy.

## Conduct

Be precise. Be terse. Disagree directly. The council is adversarial
by design and so is the project culture, but Eris-mode disagreement
is on the merits — not on the person.
