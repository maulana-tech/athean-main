"use client";

import { useAccount, useConnect, useDisconnect, useChainId, useSwitchChain } from "wagmi";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { mantleSepolia } from "@/lib/wagmi";
import { errorMessage } from "@/lib/errors";

function shorten(addr?: string) {
  return addr && addr.length >= 10 ? `${addr.slice(0, 6)}…${addr.slice(-4)}` : addr ?? "";
}

export function ConnectCard() {
  const { address, isConnected, connector } = useAccount();
  const { connectors, connect, error: connectError, isPending } = useConnect();
  const { disconnect } = useDisconnect();
  const chainId = useChainId();
  const { switchChain, isPending: switching, error: switchError } = useSwitchChain();

  const onArc = chainId === mantleSepolia.id;

  return (
    <Card className="border-primary/30">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-h4 text-foreground">
            Wallet
          </CardTitle>
          {isConnected && (
            <Badge variant={onArc ? "success" : "warning"}>
              {onArc ? "Mantle Sepolia" : `Chain ${chainId}`}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isConnected && (
          <>
            <p className="text-body text-muted-foreground">
              Pick a connector. MetaMask, Coinbase Wallet, or any
              injected EIP-1193 provider works. The whole flow runs on
              Mantle Sepolia, so you cannot lose real money — the
              connectors here are pinned to the test network.
            </p>
            <div className="flex flex-wrap gap-2">
              {connectors.map((c) => (
                <Button
                  key={c.uid}
                  onClick={() => connect({ connector: c })}
                  disabled={isPending}
                  variant="outline"
                >
                  {c.name}
                </Button>
              ))}
            </div>
            {connectError && (
              <p className="rounded-md border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">
                {errorMessage(connectError)}
              </p>
            )}
          </>
        )}

        {isConnected && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-baseline gap-3 text-sm">
              <span className="font-mono uppercase tracking-wider text-muted-foreground">
                connected
              </span>
              <code className="rounded bg-muted/30 px-2 py-0.5 font-mono text-primary">
                {shorten(address)}
              </code>
              <span className="text-xs text-muted-foreground/80">
                via {connector?.name}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {!onArc && (
                <Button
                  onClick={() => switchChain({ chainId: mantleSepolia.id })}
                  disabled={switching}
                  variant="outline"
                >
                  {switching ? "Switching…" : "Switch to Mantle Sepolia"}
                </Button>
              )}
              <Button onClick={() => disconnect()} variant="ghost">
                Disconnect
              </Button>
            </div>
            {switchError && (
              <p className="rounded-md border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">
                {errorMessage(switchError)}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
