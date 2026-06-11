# Deployment Verification — Mantle Sepolia

**Date:** 2026-06-11
**Chain:** Mantle Sepolia (chain id 5003)
**Deployer:** `0x3a8d93D5F52a26689b075A49E67F4f8924BeC84B`
**Total gas spent:** ~1.09 MNT

---

## Athean Core Contracts

Deployed via `DeployPantheon.s.sol` — block `39816558`

| Contract | Address | Explorer |
|----------|---------|----------|
| PantheonConstitution | `0x3152B6f625F25B6a2Aa0Adb57017eB74acA65ecB` | [View](https://explorer.sepolia.mantle.xyz/address/0x3152B6f625F25B6a2Aa0Adb57017eB74acA65ecB) |
| ThesisRegistry | `0xA0c9791e4FE34734D06fDD2ded0C0e0cd5b7F0f6` | [View](https://explorer.sepolia.mantle.xyz/address/0xA0c9791e4FE34734D06fDD2ded0C0e0cd5b7F0f6) |
| SignalRegistry | `0x72a86479837B87cc2aA73daBd7B54CB4DBf0AB84` | [View](https://explorer.sepolia.mantle.xyz/address/0x72a86479837B87cc2aA73daBd7B54CB4DBf0AB84) |
| AgentPassport | `0x450FB6d0f985F23c1E0F03a0c5848B7dc7Fec187` | [View](https://explorer.sepolia.mantle.xyz/address/0x450FB6d0f985F23c1E0F03a0c5848B7dc7Fec187) |
| Parthenon | `0xc5D56f02c1DaE4f13b2A6a00C2ef3C8E63f4B6F6` | [View](https://explorer.sepolia.mantle.xyz/address/0xc5D56f02c1DaE4f13b2A6a00C2ef3C8E63f4B6F6) |
| Ostrakon | `0xE67A87b2eCBbE03B90cac2cA3C494a3e1be5f615` | [View](https://explorer.sepolia.mantle.xyz/address/0xE67A87b2eCBbE03B90cac2cA3C494a3e1be5f615) |

---

## Restraint + Visitor Contracts

Deployed via `DeployRestraint.s.sol` — block `39816589`

| Contract | Address | Explorer |
|----------|---------|----------|
| ProofOfRestraint | `0xaCB12755134900196F8eE4Ae5223e6955B8Aa7Af` | [View](https://explorer.sepolia.mantle.xyz/address/0xaCB12755134900196F8eE4Ae5223e6955B8Aa7Af) |
| NoTradeAlpha | `0x1d19a197B9860bD831F84d30E51584d62796f362` | [View](https://explorer.sepolia.mantle.xyz/address/0x1d19a197B9860bD831F84d30E51584d62796f362) |
| VisitorWitness | `0xDf7939Da6366D8086E2E70cDB3d125eAdeBE7626` | [View](https://explorer.sepolia.mantle.xyz/address/0xDf7939Da6366D8086E2E70cDB3d125eAdeBE7626) |

---

## Transaction Hashes

| Deployment | Tx Hash | Block |
|------------|---------|-------|
| DeployPantheon.s.sol | [View Tx](https://explorer.sepolia.mantle.xyz/tx/) | 39816558 |
| DeployRestraint.s.sol | [View Tx](https://explorer.sepolia.mantle.xyz/tx/) | 39816589 |

---

## Broadcast Artifacts

Forge broadcast JSON saved to:
- `contracts/broadcast/DeployPantheon.s.sol/5003/run-latest.json`
- `contracts/broadcast/DeployRestraint.s.sol/5003/run-latest.json`

---

## Env Vars for .env

```bash
RPC_URL=https://rpc.sepolia.mantle.xyz
CHAIN_ID=5003
MANTLE_EXPLORER_URL=https://explorer.sepolia.mantle.xyz

PARTHENON_REGISTRY_ADDRESS=0xc5D56f02c1DaE4f13b2A6a00C2ef3C8E63f4B6F6
PANTHEON_CONSTITUTION_ADDRESS=0x3152B6f625F25B6a2Aa0Adb57017eB74acA65ecB
ERC8004_REGISTRY_ADDRESS=0x450FB6d0f985F23c1E0F03a0c5848B7dc7Fec187
PROOF_OF_RESTRAINT_ADDRESS=0xaCB12755134900196F8eE4Ae5223e6955B8Aa7Af
VISITOR_WITNESS_ADDRESS=0xDf7939Da6366D8086E2E70cDB3d125eAdeBE7626
NEXT_PUBLIC_VISITOR_WITNESS_ADDRESS=0xDf7939Da6366D8086E2E70cDB3d125eAdeBE7626
```
