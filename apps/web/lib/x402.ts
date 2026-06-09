"use client";

/**
 * x402 payment authorisation — client-side helper.
 *
 * x402 (rfc9110-style HTTP 402 Payment Required) lets a server reply
 * with a payment-required challenge that the client satisfies by
 * attaching an EIP-712 signed payment authorisation to the next
 * request. The pattern was revived by Coinbase / x402.org for
 * AI-agent micropayments and is being adopted in the ArcOSS
 * ecosystem (yield routing, escrow, prediction markets).
 *
 * For Athean's trade UI we use a constrained version: every signed
 * trade intent carries an embedded x402-style payment authorisation
 * that:
 *
 *   * Names the payer (the operator's wallet, or their session key)
 *   * Names the receiver (the on-chain ``TradeIntent`` contract on Arc)
 *   * Caps the spend at the session key's per-trade ceiling
 *   * Carries a unique nonce to prevent replay
 *   * Expires after the session key's wall-clock TTL
 *
 * The verifier (on-chain or in the API gateway) only accepts intents
 * whose embedded authorisation passes recovery + cap + expiry checks.
 *
 * Wire format
 * -----------
 * ``X-Payment`` header (base64-encoded JSON) following the x402 spec.
 * Caller does NOT call eth_sendTransaction — the receiver pulls the
 * payment in a single tx during execution, after verifying the
 * EIP-712 signature.
 */

import {
  type Hex,
  type Address,
  type PrivateKeyAccount,
  encodeAbiParameters,
  keccak256,
  toHex,
} from "viem";

/** EIP-712 domain — anchored to Mantle Sepolia + TradeIntent contract. */
export const X402_DOMAIN = {
  name: "AtheanTrades.x402",
  version: "1",
  chainId: 5003,
  // TradeIntent contract address — populated after deploy.
  verifyingContract: "0x0000000000000000000000000000000000000000" as Address,
} as const;

export const PAYMENT_AUTHORIZATION_TYPES = {
  PaymentAuthorization: [
    { name: "payer", type: "address" },
    { name: "receiver", type: "address" },
    { name: "tokenContract", type: "address" },
    { name: "amount", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" },
    { name: "purpose", type: "string" },
  ],
} as const;

export type PaymentAuthorization = {
  payer: Address;
  receiver: Address;
  tokenContract: Address;
  amount: bigint;
  validAfter: bigint;
  validBefore: bigint;
  nonce: Hex;
  purpose: string;
};

/**
 * Build a fresh PaymentAuthorization payload. Caller passes the
 * envelope fields; we mint a random 32-byte nonce + compute validity
 * window.
 */
export function buildAuthorization(args: {
  payer: Address;
  receiver: Address;
  tokenContract: Address;
  amount: bigint;
  ttlSeconds?: number;
  purpose: string;
}): PaymentAuthorization {
  const ttl = args.ttlSeconds ?? 300; // 5 min default
  const now = Math.floor(Date.now() / 1000);
  const nonceBytes = new Uint8Array(32);
  crypto.getRandomValues(nonceBytes);
  return {
    payer: args.payer,
    receiver: args.receiver,
    tokenContract: args.tokenContract,
    amount: args.amount,
    validAfter: BigInt(now),
    validBefore: BigInt(now + ttl),
    nonce: toHex(nonceBytes) as Hex,
    purpose: args.purpose,
  };
}

/**
 * Sign a PaymentAuthorization with the given session-key account.
 * Returns the EIP-712 signature ready to embed in the X-Payment
 * header.
 */
export async function signAuthorization(
  account: PrivateKeyAccount,
  authorization: PaymentAuthorization,
  verifyingContract: Address,
): Promise<Hex> {
  return account.signTypedData({
    domain: { ...X402_DOMAIN, verifyingContract },
    types: PAYMENT_AUTHORIZATION_TYPES,
    primaryType: "PaymentAuthorization",
    message: authorization,
  });
}

/**
 * Encode the (authorization, signature) tuple for the X-Payment
 * header per the x402 spec. base64 of the JSON payload — the
 * receiver decodes + verifies.
 */
export function buildPaymentHeader(
  authorization: PaymentAuthorization,
  signature: Hex,
): string {
  const payload = {
    scheme: "exact",
    network: "arc-testnet",
    payload: {
      signature,
      authorization: {
        ...authorization,
        amount: authorization.amount.toString(),
        validAfter: authorization.validAfter.toString(),
        validBefore: authorization.validBefore.toString(),
      },
    },
  };
  // btoa requires Latin-1; JSON stringify is ASCII-safe.
  return typeof window === "undefined"
    ? Buffer.from(JSON.stringify(payload)).toString("base64")
    : btoa(JSON.stringify(payload));
}

/**
 * Compute the keccak digest of a PaymentAuthorization tuple — used
 * by the on-chain verifier as the EIP-712 message hash.
 */
export function authorizationDigest(auth: PaymentAuthorization): Hex {
  return keccak256(
    encodeAbiParameters(
      [
        { type: "address" },
        { type: "address" },
        { type: "address" },
        { type: "uint256" },
        { type: "uint256" },
        { type: "uint256" },
        { type: "bytes32" },
        { type: "string" },
      ],
      [
        auth.payer,
        auth.receiver,
        auth.tokenContract,
        auth.amount,
        auth.validAfter,
        auth.validBefore,
        auth.nonce,
        auth.purpose,
      ],
    ),
  );
}
