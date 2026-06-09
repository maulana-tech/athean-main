"""Burst-seed TradeIntent submissions on Mantle Sepolia.

Generates N ephemeral payer wallets, signs an EIP-712 PaymentAuthorization
per payer with the TradeIntent's exact domain separator, then has the
funded deployer wallet submit each (auth, sig, intent) tuple. Each
submission emits a ``TradeIntentRecorded`` event with the payer's
ephemeral address as the indexed ``payer`` topic — so the dashboard
reads as N distinct operators bursting trade intents, not one wallet
hammering the contract.

Idempotent: nonces are random bytes32 per call. Re-running adds more
intents without conflicting.

Required env (from .env at repo root):
  - PRIVATE_KEY        — deployer wallet, pays gas + sends each tx
  - RPC_URL            — Mantle Sepolia JSON-RPC
  - CHAIN_ID           — 5003
  - TRADE_INTENT_ADDRESS — deployed TradeIntent contract

Run:
  uv run --project apps/api python scripts/seed_trade_intents.py --count 6
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

ROOT = Path(__file__).resolve().parent.parent
ARCSCAN = "https://testnet.explorer.sepolia.mantle.xyz"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip("'").strip('"')
        if v:
            os.environ[k] = v


load_dotenv(ROOT / ".env")

RPC_URL = os.environ["RPC_URL"]
CHAIN_ID = int(os.environ["CHAIN_ID"])
TRADE_INTENT_ADDRESS = Web3.to_checksum_address(os.environ["TRADE_INTENT_ADDRESS"])
DEPLOYER_PK = os.environ["PRIVATE_KEY"]

# Minimal ABI — just the submit function.
TRADE_INTENT_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "submit",
        "stateMutability": "nonpayable",
        "inputs": [
            {
                "name": "auth",
                "type": "tuple",
                "components": [
                    {"name": "payer", "type": "address"},
                    {"name": "receiver", "type": "address"},
                    {"name": "tokenContract", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                    {"name": "purpose", "type": "string"},
                ],
            },
            {"name": "signature", "type": "bytes"},
            {"name": "marketId", "type": "string"},
            {"name": "direction", "type": "string"},
            {"name": "councilProbabilityE6", "type": "uint256"},
            {"name": "evUsdcE6", "type": "uint256"},
        ],
        "outputs": [{"type": "uint256", "name": "intentId"}],
    }
]


# Realistic intent fixtures matching the demo's market vocabulary.
INTENT_FIXTURES = [
    {
        "marketId": "0xPM-BTC-120K-2026-07-31",
        "direction": "YES",
        "councilProbabilityE6": 615_000,  # 0.615
        "evUsdcE6": 11_240,  # +0.01124 USDC EV per dollar staked
        "purpose": "Pantheon council approval — BTC-120K",
    },
    {
        "marketId": "0xPM-ETH-3500-2026-Q2",
        "direction": "YES",
        "councilProbabilityE6": 552_000,
        "evUsdcE6": 7_810,
        "purpose": "Pantheon council approval — ETH-3500",
    },
    {
        "marketId": "0xPM-FED-RATE-CUT-MAY-2026",
        "direction": "NO",
        "councilProbabilityE6": 384_000,
        "evUsdcE6": 5_120,
        "purpose": "Pantheon council approval — FED-RATE-CUT",
    },
    {
        "marketId": "0xPM-US-ELECTION-2028-INCUMBENT",
        "direction": "NO",
        "councilProbabilityE6": 410_000,
        "evUsdcE6": 6_900,
        "purpose": "Pantheon council approval — US-2028",
    },
    {
        "marketId": "0xPM-MANIFOLD-AGI-2027",
        "direction": "YES",
        "councilProbabilityE6": 280_000,
        "evUsdcE6": 4_540,
        "purpose": "Pantheon council approval — AGI-2027",
    },
    {
        "marketId": "0xPM-NBA-FINALS-2026",
        "direction": "YES",
        "councilProbabilityE6": 525_000,
        "evUsdcE6": 3_870,
        "purpose": "Pantheon council approval — NBA-FINALS",
    },
    {
        "marketId": "0xPM-RECESSION-H2-2026",
        "direction": "NO",
        "councilProbabilityE6": 360_000,
        "evUsdcE6": 5_330,
        "purpose": "Pantheon council approval — RECESSION-H2",
    },
    {
        "marketId": "0xPM-COINBASE-IPO-2026",
        "direction": "YES",
        "councilProbabilityE6": 488_000,
        "evUsdcE6": 4_120,
        "purpose": "Pantheon council approval — COINBASE-IPO",
    },
]


def build_typed_data(auth: dict[str, Any]) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "PaymentAuthorization": [
                {"name": "payer", "type": "address"},
                {"name": "receiver", "type": "address"},
                {"name": "tokenContract", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
                {"name": "purpose", "type": "string"},
            ],
        },
        "primaryType": "PaymentAuthorization",
        "domain": {
            "name": "PantheonTrades.x402",
            "version": "1",
            "chainId": CHAIN_ID,
            "verifyingContract": TRADE_INTENT_ADDRESS,
        },
        "message": auth,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument(
        "--amount-usdc-e6",
        type=int,
        default=2_500_000,
        help="Per-intent amount in USDC 6dp units (default 2.5 USDC).",
    )
    parser.add_argument(
        "--validity-seconds",
        type=int,
        default=3600,
        help="Authorization validity window from now.",
    )
    args = parser.parse_args()

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    deployer = Account.from_key(DEPLOYER_PK)
    trade_intent = w3.eth.contract(address=TRADE_INTENT_ADDRESS, abi=TRADE_INTENT_ABI)
    now = int(time.time())

    print(f"deployer: {deployer.address}")
    print(f"chain:    {CHAIN_ID}  rpc: {RPC_URL}")
    print(f"contract: {TRADE_INTENT_ADDRESS}")
    print(f"count:    {args.count}")
    print()

    submitted: list[dict[str, Any]] = []

    for i in range(args.count):
        fixture = INTENT_FIXTURES[i % len(INTENT_FIXTURES)]
        payer = Account.create()
        nonce_bytes = secrets.token_bytes(32)
        auth = {
            "payer": payer.address,
            "receiver": deployer.address,
            "tokenContract": "0x0000000000000000000000000000000000000000",
            "amount": args.amount_usdc_e6,
            "validAfter": now - 60,
            "validBefore": now + args.validity_seconds,
            "nonce": nonce_bytes,
            "purpose": fixture["purpose"],
        }
        typed_data = build_typed_data(auth)
        signable = encode_typed_data(full_message=typed_data)
        signed = payer.sign_message(signable)

        # Build the call locally, sign with deployer, send raw. Skips the
        # web3 v7 middleware reshuffle and gives us full control over gas
        # + nonce.
        try:
            fn = trade_intent.functions.submit(
                (
                    auth["payer"],
                    auth["receiver"],
                    auth["tokenContract"],
                    auth["amount"],
                    auth["validAfter"],
                    auth["validBefore"],
                    auth["nonce"],
                    auth["purpose"],
                ),
                signed.signature,
                fixture["marketId"],
                fixture["direction"],
                fixture["councilProbabilityE6"],
                fixture["evUsdcE6"],
            )
            tx = fn.build_transaction(
                {
                    "from": deployer.address,
                    "nonce": w3.eth.get_transaction_count(deployer.address, "pending"),
                    "chainId": CHAIN_ID,
                }
            )
            signed_tx = deployer.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i+1}/{args.count}] FAILED ({fixture['marketId']}): {e}")
            continue

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        submitted.append(
            {
                "payer": payer.address,
                "market": fixture["marketId"],
                "direction": fixture["direction"],
                "block": receipt.blockNumber,
                "tx": tx_hash.hex(),
                "status": receipt.status,
            }
        )
        print(
            f"  [{i+1}/{args.count}] {fixture['marketId']:34s} "
            f"{fixture['direction']:3s}  payer={payer.address}  "
            f"block={receipt.blockNumber}  tx=0x{tx_hash.hex()[:18]}…"
        )
        # Small spacing to avoid mempool ordering races.
        time.sleep(0.5)

    print()
    print("=== TradeIntents written ===")
    for r in submitted:
        print(
            f"  block {r['block']}  payer {r['payer']}  market {r['market']}"
        )
        print(f"    {ARCSCAN}/tx/0x{r['tx']}")
    print()
    print(f"submitted: {len(submitted)}/{args.count}")
    return 0 if len(submitted) == args.count else 1


if __name__ == "__main__":
    sys.exit(main())
