/**
 * Wagmi v2 + viem configuration for Pantheon's trade UI.
 *
 * Defines Arc Testnet as the only chain, wraps the project's RPC
 * endpoint, and exports a single ``config`` consumed by
 * ``apps/web/app/providers.tsx``. Kept deliberately small —
 * connectors and chain list are the entire public surface.
 *
 * Arc Testnet:
 *   chain id            5042002 (0x4cef52)
 *   native token        USDC (18-dec internal, see MetaMask note)
 *   block time          ~1 s
 *   public RPC          https://rpc.testnet.arc.network
 *   explorer            https://testnet.arcscan.app
 *
 * No mainnet chain is registered — the trade flow stays on testnet
 * until an external smart-contract audit clears the deployed
 * contracts (see SECURITY.md).
 */

import { http, createConfig } from "wagmi";
import { defineChain } from "viem";
import { injected, metaMask, coinbaseWallet } from "wagmi/connectors";

export const arcTestnet = defineChain({
  id: 5042002,
  name: "Arc Testnet",
  network: "arc-testnet",
  nativeCurrency: {
    name: "USDC",
    symbol: "USDC",
    // MetaMask hard-validates this at 18; Arc RPC returns balances
    // in 18-decimal wei so display works out. Token-level USDC is
    // still 6-dp at the protocol layer.
    decimals: 18,
  },
  rpcUrls: {
    default: { http: ["https://rpc.testnet.arc.network"] },
    public: { http: ["https://rpc.testnet.arc.network"] },
  },
  blockExplorers: {
    default: {
      name: "Arcscan",
      url: "https://testnet.arcscan.app",
    },
  },
  testnet: true,
});

export const wagmiConfig = createConfig({
  chains: [arcTestnet],
  connectors: [
    injected({ shimDisconnect: true }),
    metaMask(),
    coinbaseWallet({
      appName: "Athean Trades",
      appLogoUrl: "https://athean-trades.vercel.app/icon.svg",
    }),
  ],
  transports: {
    [arcTestnet.id]: http(),
  },
  ssr: true,
});

declare module "wagmi" {
  interface Register {
    config: typeof wagmiConfig;
  }
}
