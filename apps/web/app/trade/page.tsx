"use client";

/**
 * /trade — operator-facing trade UI.
 *
 * Wires together everything the rest of the site has been building
 * toward: a wallet connect, a one-time session-key authorisation,
 * a market-input form that quotes the council's EV-gate output, and
 * a final sign-and-submit step that posts an x402 PaymentAuthorization
 * to the TradeIntent contract on Arc Testnet. Same theme tokens as
 * the rest of the site (text-h1 / text-lead / Card / Badge), so it
 * lands as part of the same product, not a bolt-on.
 *
 * Flow:
 *
 *   1. Connect wallet (wagmi useAccount).
 *   2. Generate + authorise a session key — one MetaMask popup
 *      that pre-approves a TTL'd ephemeral signer. Subsequent
 *      trades sign silently with the session key.
 *   3. Enter a market + direction + size. The UI calls the EV-gate
 *      quoter (client-side stub for now; routes to the API gateway
 *      once the council is wired) and shows the post-everything
 *      EV decomposition.
 *   4. If EV clears the gate, the session key signs an x402 payment
 *      authorisation. The submit step calls TradeIntent.submit()
 *      with the (auth, sig, marketId, direction, council_p, ev) tuple.
 *   5. The TradeIntentRecorded event is the receipt. Strategos
 *      (off-chain) consumes the event and routes the underlying
 *      order. This UI shows the receipt + Arcscan link.
 */

import { useState } from "react";
import { useAccount } from "wagmi";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConnectCard } from "./_components/connect-card";
import { SessionKeyPanel } from "./_components/session-key-panel";
import { TradeForm } from "./_components/trade-form";

export default function TradePage() {
  const { isConnected, address } = useAccount();
  const [sessionKeyReady, setSessionKeyReady] = useState(false);

  return (
    <div className="space-y-12 py-10">
      <header className="space-y-5">
        <span className="text-caption text-primary">
          Trade · Arc Testnet · x402 + session keys
        </span>
        <h1 className="text-h1 text-foreground">
          Run the council against a market.
        </h1>
        <p className="text-lead max-w-3xl text-muted-foreground">
          Connect a wallet, authorise an ephemeral session key (one
          MetaMask popup, TTL + spend cap), then submit market intents
          signed with x402 payment authorisations. Every accepted
          intent emits a{" "}
          <code className="font-mono text-primary">TradeIntentRecorded</code>{" "}
          event on Arc. The off-chain executor reads the event and
          routes the underlying order — same code path the live
          pipeline uses.
        </p>
      </header>

      <Card className="border-amber-500/40 bg-amber-500/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-h4 text-foreground">
            Before you start — five-minute pre-flight
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-body text-muted-foreground">
            This is the Arc Testnet operator flow. Nothing here touches a
            real Polymarket order book or a mainnet wallet. Confirm each
            item below before clicking Step 1, otherwise the wallet
            popups will read confusing.
          </p>
          <ol className="list-decimal space-y-2 pl-5 text-body text-muted-foreground">
            <li>
              <span className="text-foreground">Wallet:</span> MetaMask /
              Rabby / Coinbase Wallet, current build. The connect dialog
              uses EIP-1193, no WalletConnect.
            </li>
            <li>
              <span className="text-foreground">Network:</span> Arc
              Testnet (chain&nbsp;
              <code className="font-mono text-primary">5042002</code>,
              RPC&nbsp;
              <code className="font-mono text-primary">
                https://rpc.testnet.arc.network
              </code>
              ). Step 1 will add it for you on first connect — accept the
              prompt.
            </li>
            <li>
              <span className="text-foreground">Test USDC:</span> the
              session key and the intent submission both pay gas in
              testnet USDC. Grab a drip from the&nbsp;
              <a
                href="https://faucet.testnet.arc.network"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline-offset-4 hover:underline"
              >
                Arc Testnet faucet
              </a>
              &nbsp;if your balance is empty.
            </li>
            <li>
              <span className="text-foreground">Browser support:</span>{" "}
              session keys persist in IndexedDB — Chrome, Firefox,
              Edge, Safari 16+ work. Private / incognito windows wipe
              the key on close, so authorise again per session.
            </li>
            <li>
              <span className="text-foreground">What happens on
              submit:</span> the session key signs an x402 payment
              authorisation, the UI calls&nbsp;
              <code className="font-mono text-primary">TradeIntent.submit()</code>
              &nbsp;on Arc, and the contract emits a&nbsp;
              <code className="font-mono text-primary">
                TradeIntentRecorded
              </code>
              &nbsp;event. The off-chain executor reads the event in
              production — for this submission it stops at the event so
              no live order ships. You will get an Arcscan link to the
              receipt.
            </li>
          </ol>
          <p className="text-caption text-muted-foreground">
            All Boule deliberations on this submission are pre-recorded
            on the&nbsp;
            <a href="/demo" className="text-primary underline-offset-4 hover:underline">
              /demo
            </a>
            &nbsp;replay path — the live council costs LLM credits and
            we route those through a quota-aware fallback chain (Claude
            → Gemini 3.5 Flash → Gemini 2.5 Flash-Lite). The /trade
            route here verifies x402 + session-key plumbing end-to-end
            on chain; it does not call the LLM.
          </p>
        </CardContent>
      </Card>

      <section className="space-y-6">
        <div className="space-y-2">
          <span className="text-caption text-primary">Step 1 · wallet</span>
          <h2 className="text-h2 text-foreground">Connect.</h2>
        </div>
        <ConnectCard />
      </section>

      {isConnected && (
        <section className="space-y-6">
          <div className="space-y-2">
            <span className="text-caption text-primary">
              Step 2 · session key
            </span>
            <h2 className="text-h2 text-foreground">Authorise an ephemeral signer.</h2>
            <p className="text-body max-w-3xl text-muted-foreground">
              One MetaMask popup approves a fresh signing keypair for a
              bounded window — 5 USDC per trade, 100 USDC ceiling,
              1-hour TTL by default. After approval, every subsequent
              trade is signed silently by the session key. The key
              lives only in your browser&apos;s IndexedDB and never
              leaves.
            </p>
          </div>
          <SessionKeyPanel
            owner={address as `0x${string}`}
            onReady={setSessionKeyReady}
          />
        </section>
      )}

      {isConnected && sessionKeyReady && (
        <section className="space-y-6">
          <div className="space-y-2">
            <span className="text-caption text-primary">Step 3 · trade</span>
            <h2 className="text-h2 text-foreground">Submit an intent.</h2>
            <p className="text-body max-w-3xl text-muted-foreground">
              Pick a market and a direction. The Expected-Value gate
              computes net EV after every cost (taker fee, half-spread,
              slippage, paymaster premium) against every revenue
              (council edge, maker rebate, builder code, idle USYC
              yield). If t-stat ≥ 2.0 and EV &gt; 0, the session key
              signs the x402 payment authorisation and the intent
              lands on Arc as a TradeIntentRecorded event.
            </p>
          </div>
          <TradeForm owner={address as `0x${string}`} />
        </section>
      )}

      <Card className="border-primary/30 bg-card/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-h4 text-foreground">
            How this fits with the rest of the system
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-body text-muted-foreground">
            This UI is the operator-side counterpart to the council
            pipeline documented at{" "}
            <a
              href="/methodology"
              className="text-primary underline-offset-4 hover:underline"
            >
              /methodology
            </a>
            . The signed intent emitted here is the same event shape
            Strategos consumes in production — meaning every approval
            flowing through{" "}
            <code className="font-mono text-primary">/trade</code>{" "}
            could, once a builder-code is approved and the geo-block
            proxy is deployed, route to a real Polymarket fill.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Badge variant="success">contract live on Arc</Badge>
            <Badge variant="outline" className="border-primary/40 font-mono">
              0x3a90…c5cd
            </Badge>
            <Badge variant="outline" className="border-primary/40">
              x402 · session keys · wagmi v2 · viem
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
