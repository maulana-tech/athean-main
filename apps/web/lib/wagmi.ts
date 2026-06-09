/**
 * Wagmi v2 + viem configuration for Pantheon's trade UI.
 *
 * Defines Mantle Sepolia as the default testnet chain, with Mantle
 * mainnet available for production. Exports a single ``config``
 * consumed by ``apps/web/app/providers.tsx``.
 *
 * Mantle Sepolia (testnet):
 *   chain id     5003
 *   native token MNT (18 dec)
 *   block time   ~2 s
 *   public RPC   https://rpc.sepolia.mantle.xyz
 *   explorer     https://explorer.sepolia.mantle.xyz
 *
 * Mantle Mainnet:
 *   chain id     5000
 *   native token MNT (18 dec)
 *   public RPC   https://rpc.mantle.xyz
 *   explorer     https://explorer.mantle.xyz
 */

import { http, createConfig } from "wagmi";
import { defineChain } from "viem";
import { injected, metaMask, coinbaseWallet } from "wagmi/connectors";

export const mantleSepolia = defineChain({
  id: 5003,
  name: "Mantle Sepolia",
  network: "mantle-sepolia",
  nativeCurrency: {
    name: "MNT",
    symbol: "MNT",
    decimals: 18,
  },
  rpcUrls: {
    default: { http: ["https://rpc.sepolia.mantle.xyz"] },
    public:  { http: ["https://rpc.sepolia.mantle.xyz"] },
  },
  blockExplorers: {
    default: {
      name: "Mantle Explorer",
      url: "https://explorer.sepolia.mantle.xyz",
    },
  },
  testnet: true,
});

export const wagmiConfig = createConfig({
  chains: [mantleSepolia],
  connectors: [
    injected({ shimDisconnect: true }),
    metaMask(),
    coinbaseWallet({
      appName: "Athean Trades",
      appLogoUrl: "https://athean-trades.vercel.app/icon.svg",
    }),
  ],
  transports: {
    [mantleSepolia.id]: http(),
  },
  ssr: true,
});

declare module "wagmi" {
  interface Register {
    config: typeof wagmiConfig;
  }
}
