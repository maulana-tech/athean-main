# Security Policy

Athean Trades is a research / testnet system. Smart contracts are
deployed on Arc Testnet and the trading services route through paper
books or testnet venues by default. Even so, the code paths that handle
keys, signatures, and on-chain writes deserve treating like production
security surface — and the project benefits from external eyes.

## Reporting a vulnerability

Email security reports to `lancearmour24200@gmail.com` with the subject
prefix `[athean-trades:security]`. For sensitive findings prefer a
PGP-encrypted message; key fingerprint on request.

Please include, when applicable:

- A clear, minimal reproduction (commit SHA, code path, inputs)
- The realistic impact (key extraction, restraint forgery, fund drain,
  reentrancy, denial of service, off-by-one in sizing, etc.)
- Any proof-of-concept code or transaction hashes
- Your preferred public attribution (or `anonymous`)

You should expect:

- An acknowledgement within **72 hours**
- A confirmed-or-rejected verdict within **two weeks**
- For confirmed reports, a coordinated disclosure window of **30 days**
  before public write-up — extendable on request

## Scope (in)

- All Solidity contracts under `contracts/src/` and their deploy scripts
- All Python services under `services/` (signature handling, EIP-712,
  Redis ACL, secret loading, paymaster routing)
- The Vercel edge proxy under `apps/web/app/api/polymarket-proxy/`
- The `RestraintChainWriter` and any code path that signs an
  `eth_sendTransaction` request
- Any cryptographic primitive we re-implement (none currently — we
  use `eth_account`, `web3.py`, OpenZeppelin `AccessControl`, and
  Foundry's stdlib)

## Scope (out)

- Bugs in upstream dependencies — file those upstream first (we will
  re-pin once a fix lands)
- Test contracts under `contracts/test/`, fuzz fixtures, broadcast
  receipts, anything in `contracts/lib/` (those are pinned upstream)
- Social-engineering attacks on operators or judges
- The captured demo deliberations under `apps/web/public/demo/`
  (these are pre-recorded JSON; no live attack surface)

## Cryptographic surface — what we ship

- **Signature**: EIP-712 typed-data signing of Polymarket CLOB orders.
  Implemented via `py-clob-client`. We do not implement signing.
- **Key handling**: `PRIVATE_KEY` read from `.env`, never written to
  disk, never logged, never sent to a third-party service. Local-only.
- **Smart contracts**:
  - `PantheonConstitution` — immutable, Halmos-symbolic-verified
  - `ProofOfRestraint` — append-only, role-gated, Halmos-verified
  - `VisitorWitness` — permissionless, append-only, no admin
  - All AccessControl roles default to the deployer; transfer scripts
    in `contracts/script/Transfer*Admin.s.sol`

## What we promise

- Smart-contract source bytecode-match-verified against Arcscan after
  every deploy
- `.env` and any file matching `*.env*` is gitignored at the repo root
- Secrets-in-code lint runs as part of CI (Python syntax check + ruff
  + grep for known prefixes)
- No analytics SDKs that ship wallet addresses off-host except
  Vercel Analytics + Speed Insights (URL + UA only, no wallet)
- The Vercel edge proxy never logs the Polymarket `POLY-*` auth
  headers it forwards
- `PRIVATE_KEY` in `.env` is the deployer / testnet signer. **It is
  not a mainnet key.** Do not put a mainnet key on this machine without
  air-gapping it first.

## What we don't promise

- An external smart-contract audit. We pass Foundry tests (57) and
  Halmos symbolic verification (12 properties on the two flagship
  contracts), but no Trail-of-Bits / Sherlock / OpenZeppelin audit.
  **Do not mainnet-deploy without one.**
- Backwards-compatible behaviour. The contracts on Arc Testnet are
  immutable; the services are not. Upgrade paths are documented per
  `docs/RUNBOOK_MULTISIG_ADMIN.md` for the contract role transfers.
- Indefinite uptime of the demo at `athean-trades.vercel.app`.
  The on-chain state survives the website outage.

## Known limitations

- The visitor witness flow trusts MetaMask's chain-add to work. We
  set `decimals: 18` per the EIP-3326 hard constraint; Arc's RPC
  returns 18-decimal-style balances to match. If MetaMask changes
  its hard validation we will need to revisit.
- The Polymarket edge proxy forwards arbitrary headers if and only
  if the request originates from an allowed origin AND optionally
  carries `X-Pantheon-Proxy-Token` (set via env). Without the token
  enabled the proxy is open — sufficient for testnet reads.
- The Areopagus `RestraintChainWriter` queues retries in Redis. A
  Redis flush during an outage can lose pending anchors. Anchors
  that never land on chain are still emitted as off-chain Trace
  events — the audit trail does not disappear, it just isn't on
  chain.

## Acknowledged contributors

(empty — this section will be populated as reports come in)
