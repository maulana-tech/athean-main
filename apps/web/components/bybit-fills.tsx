"use client";

import { useEffect, useState } from "react";

type Trade = {
  trade_id: string;
  thesis_id: string;
  market_id: string;
  direction: "YES" | "NO";
  size_pct: number;
  size_usdc: number;
  entry_price: number;
  fill_price: number | null;
  status: string;
  order_id: string | null;
  fill_time: string | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function BybitFills() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchTrades() {
      try {
        const res = await fetch(`${API_URL}/trades/?limit=10`);
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json();
        setTrades(data);
        setError(null);
      } catch (e) {
        setError("Gateway unreachable");
      } finally {
        setLoading(false);
      }
    }

    fetchTrades();
    const interval = setInterval(fetchTrades, 12_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="text-body rounded-2xl border border-primary/15 bg-card/40 p-10 text-center text-muted-foreground">
        Loading recent fills…
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-body rounded-2xl border border-primary/15 bg-card/40 p-10 text-center text-muted-foreground">
        {error}. Start the API gateway to see live fills.
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <div className="text-body rounded-2xl border border-primary/15 bg-card/40 p-10 text-center text-muted-foreground">
        No fills yet. Run the council with{" "}
        <code className="text-primary">EXECUTION_MODE=bybit_paper</code> to
        see Bybit paper trades here.
      </div>
    );
  }

  return (
    <ol className="space-y-px overflow-hidden rounded-2xl border border-primary/15">
      {trades.map((t) => (
        <li
          key={t.trade_id}
          className="group grid grid-cols-[4rem_1fr_auto] items-center gap-4 bg-card/40 px-6 py-5 transition-colors hover:bg-primary/[0.04]"
        >
          <span
            className={`display text-2xl font-semibold ${
              t.direction === "YES" ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {t.direction === "YES" ? "▲" : "▼"}
          </span>
          <div>
            <div className="text-caption text-muted-foreground">
              {t.market_id}
            </div>
            <div className="mono mt-1 text-sm text-primary">
              {t.size_usdc.toFixed(2)} USDC · {t.status}
              {t.fill_price ? ` @ $${t.fill_price.toFixed(3)}` : ""}
            </div>
          </div>
          <span className="display shrink-0 text-[10px] uppercase tracking-[0.32em] text-muted-foreground">
            {t.fill_time
              ? new Date(t.fill_time).toLocaleTimeString()
              : "pending"}
          </span>
        </li>
      ))}
    </ol>
  );
}
