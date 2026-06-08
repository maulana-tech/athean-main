import type { MetadataRoute } from "next";

/**
 * Web app manifest — emitted at /manifest.webmanifest. Lets visitors
 * "Add to Home Screen" / install the demo as a PWA-style icon on
 * desktop + mobile. Light footprint, big signal on iOS/Android share
 * sheets and Chrome's omnibox install prompt.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Pantheon Trades",
    short_name: "Pantheon",
    description:
      "An eleven-agent AI council debates every prediction-market trade. Every restraint is anchored on Circle's Arc Testnet.",
    start_url: "/",
    display: "standalone",
    background_color: "#08090d",
    theme_color: "#d4a85e",
    orientation: "portrait-primary",
    categories: ["finance", "productivity", "developer", "research"],
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
  };
}
