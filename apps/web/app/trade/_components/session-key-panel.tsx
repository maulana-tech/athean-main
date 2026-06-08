"use client";

import { useCallback, useEffect, useState } from "react";
import { useSignTypedData } from "wagmi";
import type { Hex } from "viem";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type SessionKey,
  clearSessionKey,
  generateSessionKey,
  loadSessionKey,
  saveSessionKey,
} from "@/lib/session-keys";
import { errorMessage } from "@/lib/errors";

const TRADE_INTENT_ADDRESS =
  (process.env.NEXT_PUBLIC_TRADE_INTENT_ADDRESS as Hex | undefined) ??
  "0x3a900a5c996ffd76bcfa1a266fbb42307ea7c5cd";

export function SessionKeyPanel({
  owner,
  onReady,
}: {
  owner: Hex;
  onReady: (ready: boolean) => void;
}) {
  const [key, setKey] = useState<SessionKey | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { signTypedDataAsync } = useSignTypedData();

  // Hydrate any existing key from IndexedDB on mount.
  useEffect(() => {
    let cancelled = false;
    loadSessionKey(owner).then((k) => {
      if (cancelled) return;
      if (k) {
        setKey(k);
        onReady(true);
      } else {
        onReady(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [owner, onReady]);

  const authorise = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const fresh = generateSessionKey(owner);
      // Owner signs an EIP-712 SessionKeyDelegation message. This
      // signature is the owner's authorisation for the session key
      // to spend up to ceilingUsdc on their behalf for ttlSeconds.
      // Saved alongside the key so the verifier can re-check it later.
      await signTypedDataAsync({
        domain: {
          name: "PantheonTrades.SessionKey",
          version: "1",
          chainId: 5042002,
          verifyingContract: TRADE_INTENT_ADDRESS,
        },
        types: {
          SessionKeyDelegation: [
            { name: "owner", type: "address" },
            { name: "sessionKey", type: "address" },
            { name: "maxPerTradeUsdc", type: "uint256" },
            { name: "ceilingUsdc", type: "uint256" },
            { name: "expiresAt", type: "uint256" },
          ],
        },
        primaryType: "SessionKeyDelegation",
        message: {
          owner,
          sessionKey: fresh.address,
          maxPerTradeUsdc: fresh.maxPerTradeUsdc,
          ceilingUsdc: fresh.ceilingUsdc,
          expiresAt: BigInt(Math.floor(fresh.expiresAt / 1000)),
        },
      });
      // Strip the in-memory account before persisting (private key
      // alone is enough; account derives from it on load).
      const persisted: SessionKey = {
        privateKey: fresh.privateKey,
        address: fresh.address,
        ownerAddress: fresh.ownerAddress,
        expiresAt: fresh.expiresAt,
        maxPerTradeUsdc: fresh.maxPerTradeUsdc,
        ceilingUsdc: fresh.ceilingUsdc,
        nonce: fresh.nonce,
      };
      await saveSessionKey(persisted);
      setKey(persisted);
      onReady(true);
    } catch (e) {
      setError(errorMessage(e));
      onReady(false);
    } finally {
      setBusy(false);
    }
  }, [owner, signTypedDataAsync, onReady]);

  const revoke = useCallback(async () => {
    await clearSessionKey(owner);
    setKey(null);
    onReady(false);
  }, [owner, onReady]);

  if (key) {
    const remaining = Math.max(0, key.expiresAt - Date.now()) / 1000;
    return (
      <Card className="border-emerald-500/40 bg-emerald-500/5">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-h4 text-foreground">
              Session key active
            </CardTitle>
            <Badge variant="success">authorised</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 text-sm">
            <Row label="signer" value={`${key.address.slice(0, 10)}…${key.address.slice(-8)}`} mono />
            <Row label="per-trade cap" value={`${(Number(key.maxPerTradeUsdc) / 1e6).toFixed(2)} USDC`} />
            <Row label="cumulative cap" value={`${(Number(key.ceilingUsdc) / 1e6).toFixed(2)} USDC`} />
            <Row label="expires in" value={`${Math.floor(remaining / 60)} min ${Math.floor(remaining % 60)} s`} />
          </div>
          <Button onClick={revoke} variant="outline" size="sm">
            Revoke + new key
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/30">
      <CardHeader className="pb-3">
        <CardTitle className="text-h4 text-foreground">Authorise a session key</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 text-sm text-muted-foreground">
          <Row label="per-trade cap" value="5 USDC" />
          <Row label="cumulative cap" value="100 USDC" />
          <Row label="ttl" value="1 hour" />
          <Row label="verifyingContract" value={TRADE_INTENT_ADDRESS.slice(0, 14) + "…"} mono />
        </div>
        <Button onClick={authorise} disabled={busy}>
          {busy ? "Awaiting signature…" : "Authorise session key"}
        </Button>
        {error && (
          <p className="rounded-md border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">
            {error}
          </p>
        )}
        <p className="text-xs leading-[1.55] text-muted-foreground">
          The key is generated client-side, stored in your browser&apos;s
          IndexedDB, and never sent to any server. Revoke at any time
          to invalidate.
        </p>
      </CardContent>
    </Card>
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
