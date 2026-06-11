"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

/**
 * Top-of-page on-chain ticker. Polls Mantle Sepolia via JSON-RPC for
 * the current block number, shows the live counter, and links the
 * first ProofOfRestraint witness to the Mantle explorer.
 *
 * Server-friendly: degrades gracefully on RPC failure — block height
 * just stays static.
 */

const MANTLE_RPC = "https://rpc.sepolia.mantle.xyz";
const MANTLE_EXPLORER = "https://explorer.sepolia.mantle.xyz";
const FIRST_PROOF_TX =
  process.env.NEXT_PUBLIC_FIRST_PROOF_TX ?? "";
const POR_CONTRACT =
  process.env.NEXT_PUBLIC_PROOF_OF_RESTRAINT_ADDRESS ?? "";

export function ChainTicker() {
  const [block, setBlock] = useState<number | null>(null);
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval>;

    async function fetchBlock() {
      try {
        const r = await fetch(MANTLE_RPC, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            jsonrpc: "2.0",
            id: 1,
            method: "eth_blockNumber",
            params: [],
          }),
        });
        const j = await r.json();
        const n = parseInt(j.result, 16);
        if (!cancelled && Number.isFinite(n)) {
          setBlock(n);
          setPulse(true);
          setTimeout(() => !cancelled && setPulse(false), 800);
        }
      } catch {
        // RPC unreachable — leave previous value
      }
    }

    fetchBlock();
    timer = setInterval(fetchBlock, 30_000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return (
    <div className="border-b border-primary/15 bg-background/75 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-2.5 text-[11px]">
        <div className="mono flex items-center gap-2 text-muted-foreground">
          <motion.span
            className="inline-block size-1.5 rounded-full bg-emerald-400"
            animate={pulse ? { scale: [1, 2, 1], opacity: [1, 0.6, 1] } : {}}
            transition={{ duration: 0.8 }}
          />
          <span className="hidden sm:inline">Mantle Sepolia · live</span>
          <span className="sm:hidden">live</span>
          <span className="opacity-50">·</span>
          <span>
            block{" "}
            <span className="text-primary">
              {block !== null ? block.toLocaleString() : "—"}
            </span>
          </span>
        </div>

        <a
          href={`${MANTLE_EXPLORER}/tx/${FIRST_PROOF_TX}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mono group hidden items-center gap-2 text-muted-foreground transition-colors hover:text-primary md:flex"
          title="First on-chain restraint witness"
        >
          <span className="opacity-70">restraint #1</span>
          <span className="truncate">
            {FIRST_PROOF_TX.slice(0, 10)}…{FIRST_PROOF_TX.slice(-6)}
          </span>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            className="size-3 transition-transform group-hover:translate-x-0.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </a>

        <a
          href={`${MANTLE_EXPLORER}/address/${POR_CONTRACT}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mono text-muted-foreground transition-colors hover:text-primary"
        >
          0xaCB1…a7Af
        </a>
      </div>
    </div>
  );
}
