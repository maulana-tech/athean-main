import { ImageResponse } from "next/og";

/**
 * Site-wide OpenGraph image — rendered by Next at build/request time
 * via the Edge ImageResponse runtime. Lives at /opengraph-image so any
 * platform that reads the og:image meta tag (LinkedIn, X, Slack,
 * Discord, WhatsApp, Telegram) pulls this 1200×630 card.
 *
 * No external font fetch — uses system fallback so the route stays
 * cacheable indefinitely and survives a network outage on the edge.
 */

export const runtime = "edge";
export const alt = "Pantheon Trades — A council of eleven gods debates every trade.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OG() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          backgroundColor: "#08090d",
          color: "#f4ead3",
          fontFamily: "serif",
          backgroundImage:
            "radial-gradient(ellipse 80% 60% at 12% 0%, rgba(212,168,94,0.18), transparent 60%), radial-gradient(ellipse 80% 60% at 88% 100%, rgba(56,72,96,0.25), transparent 60%)",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              color: "#d4a85e",
              fontSize: 18,
              letterSpacing: 8,
              textTransform: "uppercase",
            }}
          >
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: 5,
                backgroundColor: "#d4a85e",
              }}
            />
            Pantheon Trades · Mantle Sepolia · chain 5003
          </div>
          <div
            style={{
              fontSize: 88,
              fontWeight: 600,
              lineHeight: 1.02,
              letterSpacing: "-0.018em",
              color: "#f4ead3",
            }}
          >
            A council of eleven gods
            <br />
            debates every trade.
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div
            style={{
              fontSize: 30,
              lineHeight: 1.4,
              color: "#cfc4a4",
              maxWidth: 980,
              fontStyle: "italic",
            }}
          >
            Every approval — and every restraint — is anchored on Circle&apos;s Mantle Sepolia.
            No-trade alpha, made auditable.
          </div>
          <div
            style={{
              display: "flex",
              gap: 28,
              color: "#d4a85e",
              fontSize: 22,
              letterSpacing: 4,
            }}
          >
            <span>11 agents</span>
            <span style={{ color: "#6b6655" }}>·</span>
            <span>4 rounds</span>
            <span style={{ color: "#6b6655" }}>·</span>
            <span>0.149 Brier</span>
            <span style={{ color: "#6b6655" }}>·</span>
            <span>714 tests</span>
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
