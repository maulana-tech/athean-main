"use client";

/**
 * Session-key utility.
 *
 * A "session key" is an ephemeral signing keypair that the operator
 * approves once and then uses to sign many low-value trade intents
 * without further MetaMask prompts. Conceptually identical to ERC-4337
 * smart-account session keys but implemented here as a pure
 * client-side EOA key persisted in IndexedDB, scoped to the Arc
 * Testnet ``TradeIntent`` contract, time-bound, and capped at a
 * per-trade USDC ceiling.
 *
 * Why this matters
 * ----------------
 * Without a session key, every trade requires a full MetaMask popup —
 * connect → approve → sign → wait → confirm. That's fine for one
 * tx, terrible for a system that fires several per minute when the
 * council is hot. The session-key delegation pattern lets the
 * operator sign a single SIWE-style authorisation that pre-approves
 * the session key for N minutes / M USDC, after which the UI signs
 * subsequent intents silently using the session key.
 *
 * Security envelope
 * -----------------
 *  * Session keys NEVER leave the browser. They live in IndexedDB
 *    under the origin, are bound to a single account address, and
 *    expire by wall-clock time.
 *  * The signed authorisation includes the session key's public
 *    address, the spend ceiling, and the expiry — so even if a
 *    session key leaks, the upstream verifier rejects intents that
 *    exceed the envelope.
 *  * Lost / compromised session keys are revoked by clearing the
 *    IndexedDB entry and signing a new authorisation. The on-chain
 *    contract checks the timestamp + signer address per intent.
 *
 * This module is the *client* half. The contract half lives in
 * ``contracts/src/TradeIntent.sol``.
 */

import type { Hex } from "viem";
import {
  type PrivateKeyAccount,
  privateKeyToAccount,
  generatePrivateKey,
} from "viem/accounts";

const DB_NAME = "pantheon-session-keys";
const STORE = "keys";
const VERSION = 1;

export type SessionKey = {
  /** Hex-encoded private key. NEVER leaves the browser. */
  privateKey: Hex;
  /** Public address derived from the private key. */
  address: Hex;
  /** Owner wallet address (the MetaMask account that signed the
   *  authorisation). One owner can hold many session keys. */
  ownerAddress: Hex;
  /** Unix-millis expiry. Reads / writes ignore the key past this. */
  expiresAt: number;
  /** Max per-trade size in USDC (6dp wei). Verifier enforces. */
  maxPerTradeUsdc: bigint;
  /** Total cumulative ceiling in USDC (6dp wei). */
  ceilingUsdc: bigint;
  /** Counter so the verifier can dedupe replays. */
  nonce: number;
};

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "ownerAddress" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Generate a fresh session key for the given owner. The caller MUST
 * follow up with a wallet-side authorisation signing step before
 * actually using the key.
 */
export function generateSessionKey(
  ownerAddress: Hex,
  opts: {
    maxPerTradeUsdc?: bigint;
    ceilingUsdc?: bigint;
    ttlSeconds?: number;
  } = {},
): SessionKey & { account: PrivateKeyAccount } {
  const {
    maxPerTradeUsdc = 5_000_000n, // 5 USDC default (6-dp)
    ceilingUsdc = 100_000_000n, // 100 USDC default (6-dp)
    ttlSeconds = 3600, // 1h default
  } = opts;
  const privateKey = generatePrivateKey();
  const account = privateKeyToAccount(privateKey);
  return {
    privateKey,
    address: account.address,
    ownerAddress,
    expiresAt: Date.now() + ttlSeconds * 1000,
    maxPerTradeUsdc,
    ceilingUsdc,
    nonce: 0,
    account,
  };
}

export async function saveSessionKey(key: SessionKey): Promise<void> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    // serialise bigints to string for IDB storage
    const persisted = {
      ...key,
      maxPerTradeUsdc: key.maxPerTradeUsdc.toString(),
      ceilingUsdc: key.ceilingUsdc.toString(),
    };
    store.put(persisted);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function loadSessionKey(
  ownerAddress: Hex,
): Promise<(SessionKey & { account: PrivateKeyAccount }) | null> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const store = tx.objectStore(STORE);
    const req = store.get(ownerAddress);
    req.onsuccess = () => {
      const raw = req.result as
        | (Omit<SessionKey, "maxPerTradeUsdc" | "ceilingUsdc"> & {
            maxPerTradeUsdc: string;
            ceilingUsdc: string;
          })
        | undefined;
      if (!raw) return resolve(null);
      if (raw.expiresAt < Date.now()) {
        // Stale — proactively drop to keep storage tidy.
        const wtx = db.transaction(STORE, "readwrite");
        wtx.objectStore(STORE).delete(ownerAddress);
        return resolve(null);
      }
      const key: SessionKey = {
        ...raw,
        maxPerTradeUsdc: BigInt(raw.maxPerTradeUsdc),
        ceilingUsdc: BigInt(raw.ceilingUsdc),
      };
      resolve({ ...key, account: privateKeyToAccount(key.privateKey) });
    };
    req.onerror = () => reject(req.error);
  });
}

export async function clearSessionKey(ownerAddress: Hex): Promise<void> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete(ownerAddress);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
