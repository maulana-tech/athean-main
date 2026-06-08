"use client";

/**
 * Root-level providers. Wraps the app in WagmiProvider +
 * QueryClientProvider so any client component below can use
 * ``useAccount``, ``useChainId``, ``useSignTypedData`` etc out of the
 * box. QueryClient is instantiated lazily inside ``useState`` to
 * survive Next.js hot reload + SSR.
 *
 * Only mounted as a child of ``<body>``; the existing RevealProvider
 * stays where it is so server components above this point are
 * unaffected.
 */

import { useState, type ReactNode } from "react";
import { WagmiProvider } from "wagmi";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { wagmiConfig } from "@/lib/wagmi";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 30s stale matches the dashboard revalidate window so
            // wallet-driven balance reads don't hammer the public RPC.
            staleTime: 30_000,
            // Keep one in-flight retry; transient network failures
            // shouldn't surface as red toasts.
            retry: 1,
          },
        },
      }),
  );
  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </WagmiProvider>
  );
}
