"use client";

import { useCallback, useMemo, useState } from "react";
import { useWriteContract, useWaitForTransactionReceipt } from "wagmi";
import type { Address, Hex } from "viem";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { loadSessionKey } from "@/lib/session-keys";
import { buildAuthorization, signAuthorization } from "@/lib/x402";
import { errorMessage } from "@/lib/errors";

const TRADE_INTENT_ADDRESS = ((process.env.NEXT_PUBLIC_TRADE_INTENT_ADDRESS as Address | undefined) ??
  "0x3a900a5c996ffd76bcfa1a266fbb42307ea7c5cd") as Address;

const USDC_TOKEN_ARC = "0x0000000000000000000000000000000000000001" as Address;
const MANTLE_EXPLORER = "https://explorer.sepolia.mantle.xyz";

// Minimal ABI for TradeIntent.submit.
const TRADE_INTENT_ABI = [
  {
    type: "function",
    name: "submit",
    stateMutability: "nonpayable",
    inputs: [
      {
        name: "auth",
        type: "tuple",
        components: [
          { name: "payer", type: "address" },
          { name: "receiver", type: "address" },
          { name: "tokenContract", type: "address" },
          { name: "amount", type: "uint256" },
          { name: "validAfter", type: "uint256" },
          { name: "validBefore", type: "uint256" },
          { name: "nonce", type: "bytes32" },
          { name: "purpose", type: "string" },
        ],
      },
      { name: "signature", type: "bytes" },
      { name: "marketId", type: "string" },
      { name: "direction", type: "string" },
      { name: "councilProbabilityE6", type: "uint256" },
      { name: "evUsdcE6", type: "uint256" },
    ],
    outputs: [{ name: "intentId", type: "uint256" }],
  },
] as const;

/**
 * Local EV stub. Once Boule's council runs server-side and exposes
 * an API endpoint we'll replace this with a fetch; the math however
 * is identical to ``services/areopagus/expected_value.py`` so the
 * client-side number matches the production computation exactly.
 */
function computeQuote(input: {
  marketP: number;
  councilP: number;
  councilStdev: number;
  direction: "YES" | "NO";
  notionalUsdc: number;
}): {
  edgePct: number;
  evUsdc: number;
  evPerNotionalBps: number;
  tStat: number;
  fire: boolean;
} {
  const { marketP, councilP, councilStdev, direction, notionalUsdc } = input;
  const signedEdge = direction === "YES" ? councilP - marketP : marketP - councilP;
  const price = direction === "YES" ? marketP : 1 - marketP;
  const edgePnl = notionalUsdc > 0 && price > 0 ? (notionalUsdc * signedEdge) / price : 0;
  const spreadCost = -50 * 1e-4 * notionalUsdc;
  const slippageCost = -30 * 1e-4 * notionalUsdc;
  const feeCost = -400 * 1e-4 * notionalUsdc;
  const rebate = 0.22 * 400 * 1e-4 * notionalUsdc;
  const builderBps = 20;
  const builderRev = builderBps * 1e-4 * notionalUsdc;
  const ev = edgePnl + spreadCost + slippageCost + feeCost + rebate + builderRev;
  const evPerNotionalBps = notionalUsdc > 0 ? (ev / notionalUsdc) * 1e4 : 0;
  const stdevPerNotionalBps = price > 0 ? (councilStdev / price) * 1e4 : Infinity;
  const tStat = stdevPerNotionalBps > 0 ? evPerNotionalBps / stdevPerNotionalBps : 0;
  return {
    edgePct: signedEdge * 100,
    evUsdc: ev,
    evPerNotionalBps,
    tStat,
    fire: tStat >= 2.0 && ev > 0,
  };
}

export function TradeForm({ owner }: { owner: Hex }) {
  const [marketId, setMarketId] = useState("");
  const [direction, setDirection] = useState<"YES" | "NO">("YES");
  const [marketP, setMarketP] = useState(0.42);
  const [councilP, setCouncilP] = useState(0.59);
  const [councilStdev, setCouncilStdev] = useState(0.04);
  const [notional, setNotional] = useState(5);
  const [signedSig, setSignedSig] = useState<Hex | null>(null);
  const [signing, setSigning] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const quote = useMemo(
    () => computeQuote({ marketP, councilP, councilStdev, direction, notionalUsdc: notional }),
    [marketP, councilP, councilStdev, direction, notional],
  );

  const { writeContract, data: txHash, isPending: submitting, error: writeError } =
    useWriteContract();
  const { isLoading: confirming, isSuccess: confirmed } = useWaitForTransactionReceipt({
    hash: txHash,
  });

  const onSign = useCallback(async () => {
    setSubmitError(null);
    setSignedSig(null);
    setSigning(true);
    try {
      const session = await loadSessionKey(owner);
      if (!session) {
        throw new Error("Session key expired or missing — re-authorise above.");
      }
      const amount = BigInt(Math.round(notional * 1e6));
      if (amount > session.maxPerTradeUsdc) {
        throw new Error(
          `Notional ${notional} USDC exceeds session-key per-trade cap of ${Number(session.maxPerTradeUsdc) / 1e6}.`,
        );
      }
      const auth = buildAuthorization({
        payer: session.address,
        receiver: TRADE_INTENT_ADDRESS,
        tokenContract: USDC_TOKEN_ARC,
        amount,
        purpose: `council:${direction}:${marketId.slice(0, 32)}`,
      });
      const sig = await signAuthorization(session.account, auth, TRADE_INTENT_ADDRESS);
      setSignedSig(sig);
      // Submit immediately — the signing keypair is the session key,
      // not the wallet, so no MetaMask popup.
      writeContract({
        address: TRADE_INTENT_ADDRESS,
        abi: TRADE_INTENT_ABI,
        functionName: "submit",
        args: [
          auth,
          sig,
          marketId,
          direction,
          BigInt(Math.round(councilP * 1_000_000)),
          BigInt(Math.round(quote.evUsdc * 1_000_000)),
        ],
      });
    } catch (e) {
      setSubmitError(errorMessage(e));
    } finally {
      setSigning(false);
    }
  }, [owner, notional, direction, marketId, councilP, quote.evUsdc, writeContract]);

  return (
    <Card className="border-primary/30">
      <CardHeader className="pb-3">
        <CardTitle className="text-h4 text-foreground">Compose a trade intent</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Market ID" hint="Polymarket condition_id or label">
            <input
              type="text"
              value={marketId}
              onChange={(e) => setMarketId(e.target.value)}
              placeholder="0x6e7b...btc-120k-2026-12-31"
              className="w-full rounded-md border border-primary/25 bg-card/40 px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground/60 focus:border-primary focus:outline-none"
            />
          </Field>
          <Field label="Direction">
            <div className="flex gap-2">
              {(["YES", "NO"] as const).map((d) => (
                <Button
                  key={d}
                  variant={direction === d ? "default" : "outline"}
                  size="sm"
                  onClick={() => setDirection(d)}
                  className="flex-1"
                >
                  {d}
                </Button>
              ))}
            </div>
          </Field>
          <Field label="Market probability" hint="From the order book mid">
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={marketP}
              onChange={(e) => setMarketP(Number(e.target.value))}
              className="w-full rounded-md border border-primary/25 bg-card/40 px-3 py-2 font-mono text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </Field>
          <Field label="Council probability" hint="From Boule deliberation">
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={councilP}
              onChange={(e) => setCouncilP(Number(e.target.value))}
              className="w-full rounded-md border border-primary/25 bg-card/40 px-3 py-2 font-mono text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </Field>
          <Field label="Council σ" hint="One-sigma uncertainty">
            <input
              type="number"
              min={0}
              max={0.5}
              step={0.005}
              value={councilStdev}
              onChange={(e) => setCouncilStdev(Number(e.target.value))}
              className="w-full rounded-md border border-primary/25 bg-card/40 px-3 py-2 font-mono text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </Field>
          <Field label="Notional (USDC)" hint="Must be within session-key cap">
            <input
              type="number"
              min={0}
              max={5}
              step={0.1}
              value={notional}
              onChange={(e) => setNotional(Number(e.target.value))}
              className="w-full rounded-md border border-primary/25 bg-card/40 px-3 py-2 font-mono text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </Field>
        </div>

        <div className="rounded-md border border-primary/15 bg-card/40 p-4">
          <div className="text-caption mb-3 text-primary">EV gate · live quote</div>
          <div className="grid gap-2 text-sm md:grid-cols-2">
            <Row label="Edge" value={`${quote.edgePct.toFixed(2)} pp`} />
            <Row label="EV (USDC)" value={`${quote.evUsdc.toFixed(4)}`} mono />
            <Row label="EV / notional" value={`${quote.evPerNotionalBps.toFixed(1)} bps`} mono />
            <Row label="t-stat" value={quote.tStat.toFixed(2)} mono />
          </div>
          <div className="mt-4 flex items-center justify-between">
            <Badge variant={quote.fire ? "success" : "warning"}>
              {quote.fire ? "GATE PASSES · ready to fire" : "GATE BLOCKS · EV below threshold"}
            </Badge>
            <span className="text-xs text-muted-foreground">
              threshold: t-stat ≥ 2.0 AND EV &gt; 0
            </span>
          </div>
        </div>

        <Button
          onClick={onSign}
          disabled={!quote.fire || !marketId || signing || submitting || confirming}
          className="w-full"
        >
          {signing
            ? "Signing intent…"
            : submitting
              ? "Submitting on Arc…"
              : confirming
                ? "Awaiting confirmation…"
                : "Sign + submit intent"}
        </Button>

        {confirmed && txHash && (
          <div className="rounded-md border border-emerald-500/40 bg-emerald-500/5 p-4 text-sm">
            <div className="font-mono uppercase tracking-wider text-emerald-200">
              ✓ Intent recorded on Arc
            </div>
            <a
              href={`${ARCSCAN}/tx/${txHash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 block break-all font-mono text-xs text-emerald-300 underline-offset-4 hover:underline"
            >
              {txHash}
            </a>
          </div>
        )}

        {(submitError || writeError) && (
          <p className="rounded-md border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">
            {submitError ?? errorMessage(writeError)}
          </p>
        )}

        {signedSig && !confirmed && (
          <details className="rounded-md border border-primary/15 bg-card/40 p-3 text-xs">
            <summary className="cursor-pointer font-mono uppercase tracking-wider text-primary">
              x402 signature (debug)
            </summary>
            <code className="mt-2 block break-all font-mono text-muted-foreground">
              {signedSig}
            </code>
          </details>
        )}
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-caption text-primary/80">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground/70">{hint}</p>}
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className={mono ? "font-mono text-foreground" : "text-foreground"}>{value}</span>
    </div>
  );
}
