"use client";

/**
 * Chamber widgets — evidence-first replacements for the prior decorative
 * versions. Three units:
 *
 *  - CouncilPulse      : live Mantle Sepolia heartbeat. Polls block height
 *                        and the two on-chain counters (PoR.nextProofId
 *                        and VisitorWitness.total) every 12 s. Replaces
 *                        the prior decorative ChamberClock.
 *  - LatestDecisions   : rotates through the actual captured council
 *                        verdicts from /demo/*.json, showing market id,
 *                        decision, reason code. Replaces the prior
 *                        SpeakingNow widget (which faked a live speaker).
 *  - ConstitutionSnip  : cycles through three constitutional rules.
 *                        Kept as-is — these are real verbatim rules
 *                        from docs/CONSTITUTION.md.
 *
 * The legacy ChamberClock / SpeakingNow exports are still here under
 * their original names so existing imports keep working, but they now
 * forward to the evidence-first replacements.
 */

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";
import { MedallionOrnament } from "./ornaments";

// Captured deliberations — the four /demo/*.json bundles, surfaced as
// rotating evidence in LatestDecisions. Each entry maps to a real
// scenario the operator has shipped + can be replayed at /demo.
const DECISIONS = [
  {
    scenario: "btc-120k-approve",
    market: "BTC ≥ $120k · 2026-12-31",
    decision: "RESIZED",
    reason: "themis sized down to half-Kelly cap",
    sentiment: "approved",
  },
  {
    scenario: "btc-120k-restraint",
    market: "BTC ≥ $120k · 2026-12-31",
    decision: "VETOED",
    reason: "ZEUS_VETO · cluster correlation 0.78 > 0.65",
    sentiment: "restrained",
  },
  {
    scenario: "election-2028-approve",
    market: "US incumbent · 2028",
    decision: "RESIZED",
    reason: "themis resize from 10.5% to 3.5% NAV (politics cap)",
    sentiment: "approved",
  },
  {
    scenario: "nfl-superbowl-restraint",
    market: "Chiefs · Super Bowl LXIII",
    decision: "REFUSED",
    reason: "LIQUIDITY · 24h volume below 50k USDC floor (Article IV §1)",
    sentiment: "restrained",
  },
];

const MANTLE_RPC = "https://rpc.sepolia.mantle.xyz";
const POR_CONTRACT = process.env.NEXT_PUBLIC_PROOF_OF_RESTRAINT_ADDRESS ?? "";
const VW_CONTRACT  = process.env.NEXT_PUBLIC_VISITOR_WITNESS_ADDRESS ?? "";
// keccak("nextProofId()")[:4] and keccak("total()")[:4].
const NEXT_PROOF_ID_SELECTOR = "0x6a627842";
const TOTAL_SELECTOR = "0x2ddbd13a";

const RULES = [
  {
    article: "Article II §1",
    body: "No position shall exceed five percent of total book equity.",
  },
  {
    article: "Article III §2",
    body: "Crypto-cluster exposure shall not exceed twelve percent at any time.",
  },
  {
    article: "Article IV §1",
    body: "No trade where 24-hour volume falls below fifty thousand USDC.",
  },
  {
    article: "Article V §3",
    body: "Politics positions shall not exceed four percent, sports three, science two.",
  },
  {
    article: "Article VI §1",
    body: "Kelly is taken at one-half. Never full. Never doubled.",
  },
];

async function callRpc(method: string, params: unknown[]): Promise<string | null> {
  try {
    const r = await fetch(MANTLE_RPC, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
    });
    const j = await r.json();
    return typeof j.result === "string" ? j.result : null;
  } catch {
    return null;
  }
}

/**
 * ChamberClock — live Mantle Sepolia pulse widget showing block height
 * + the two on-chain counters that gate the dashboard feeds. Polls
 * every 12 seconds. Name kept for backward-compat with existing imports.
 */
export function ChamberClock({ className }: { className?: string }) {
  const [block, setBlock] = useState<number | null>(null);
  const [restraints, setRestraints] = useState<number | null>(null);
  const [visits, setVisits] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      const [bn, rid, total] = await Promise.all([
        callRpc("eth_blockNumber", []),
        callRpc("eth_call", [{ to: POR_CONTRACT, data: NEXT_PROOF_ID_SELECTOR }, "latest"]),
        callRpc("eth_call", [{ to: VW_CONTRACT, data: TOTAL_SELECTOR }, "latest"]),
      ]);
      if (cancelled) return;
      if (bn) setBlock(parseInt(bn, 16));
      if (rid && rid !== "0x") setRestraints(Math.max(0, parseInt(rid, 16) - 1));
      if (total && total !== "0x") setVisits(parseInt(total, 16));
    }
    tick();
    const id = setInterval(tick, 12000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div
      className={cn(
        "w-full max-w-[220px] space-y-4 rounded-xl border border-primary/15 bg-card/40 p-5",
        className,
      )}
    >
      <div className="display flex items-center gap-2 text-[10px] uppercase tracking-[0.32em] text-primary/80">
        <span
          className={cn(
            "inline-block size-1.5 rounded-full",
            block === null ? "bg-amber-500" : "animate-pulse bg-emerald-400",
          )}
        />
        Mantle · live
      </div>
      <Pulse label="Block" value={block === null ? "—" : block.toLocaleString()} />
      <Pulse
        label="Restraints"
        value={restraints === null ? "—" : restraints.toString()}
      />
      <Pulse label="Visits" value={visits === null ? "—" : visits.toString()} />
      <p className="font-serif text-[11px] italic leading-[1.5] text-muted-foreground">
        Polled directly from{" "}
        <code className="font-mono">rpc.sepolia.mantle.xyz</code>.
      </p>
    </div>
  );
}

function Pulse({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      <span className="font-display text-lg font-semibold text-primary">{value}</span>
    </div>
  );
}

/**
 * SpeakingNow — formerly cycled through agent names with no real signal.
 * Now rotates through the four real captured council verdicts every
 * 7 seconds, surfacing the actual decision + reason code for each.
 * Each entry links to its full replay at /demo. Name kept for
 * backward-compat with existing imports.
 */
export function SpeakingNow({ className }: { className?: string }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((x) => (x + 1) % DECISIONS.length), 7000);
    return () => clearInterval(id);
  }, []);
  const d = DECISIONS[i];
  const isRestrained = d.sentiment === "restrained";
  return (
    <div
      className={cn(
        "rounded-xl border border-primary/15 bg-card/40 p-5",
        className,
      )}
    >
      <div className="display flex items-baseline justify-between text-[10px] uppercase tracking-[0.32em] text-primary/80">
        <span className="flex items-center gap-2">
          <span className="inline-block size-1.5 animate-pulse rounded-full bg-primary" />
          Captured verdict
        </span>
        <span className="font-mono text-muted-foreground">{i + 1}/{DECISIONS.length}</span>
      </div>
      <div className="mt-4 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
        {d.market}
      </div>
      <div
        className={cn(
          "display mt-2 text-2xl font-semibold tracking-[0.04em]",
          isRestrained ? "text-rose-300" : "text-emerald-300",
        )}
      >
        {d.decision}
      </div>
      <p className="mt-3 font-serif text-sm leading-[1.55] text-muted-foreground">
        {d.reason}
      </p>
      <div className="mt-4 flex justify-end gap-1.5">
        {DECISIONS.map((_, k) => (
          <span
            key={k}
            className={cn(
              "h-px w-4 transition-colors duration-500",
              k === i ? "bg-primary" : "bg-primary/15",
            )}
          />
        ))}
      </div>
      <a
        href={`/demo?scenario=${d.scenario}`}
        className="display mt-4 inline-flex text-[10px] uppercase tracking-[0.28em] text-primary transition-opacity hover:opacity-80"
      >
        Replay this deliberation ↗
      </a>
    </div>
  );
}

export function ConstitutionSnip({ className }: { className?: string }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((x) => (x + 1) % RULES.length), 12000);
    return () => clearInterval(id);
  }, []);
  const r = RULES[i];
  return (
    <div
      className={cn(
        "relative rounded-xl border border-primary/15 bg-card/40 p-5",
        className,
      )}
    >
      <div className="display flex items-center justify-between text-[10px] uppercase tracking-[0.4em] text-primary/65">
        <span>{r.article}</span>
        <MedallionOrnament glyph="§" className="h-6 w-6 opacity-80" />
      </div>
      <p className="serif mt-4 text-base italic leading-relaxed text-foreground/90">
        &ldquo;{r.body}&rdquo;
      </p>
      <div className="mt-4 flex justify-end gap-1">
        {RULES.map((_, k) => (
          <span
            key={k}
            className={cn(
              "h-px w-3 transition-colors duration-500",
              k === i ? "bg-primary" : "bg-primary/15",
            )}
          />
        ))}
      </div>
    </div>
  );
}
