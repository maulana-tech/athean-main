import type { MetadataRoute } from "next";

/**
 * Sitemap — emitted as /sitemap.xml at build time.
 *
 * Lists every public route so search engines can crawl + index. The
 * static routes are the canonical front door. Demo scenarios are
 * enumerated as separate URLs because each one is a distinct piece
 * of indexable content (different captured deliberation, different
 * verdict, different market).
 */

const BASE = "https://athean-trades.vercel.app";

const SCENARIOS = [
  "btc-120k-approve",
  "btc-120k-restraint",
  "election-2028-approve",
  "nfl-superbowl-restraint",
];

const AGENTS = [
  "ares",
  "hades",
  "athena",
  "cassandra",
  "zeus",
  "solon",
  "themis",
  "hephaestus",
  "daedalus",
  "humans",
  "eris",
];

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  const top: MetadataRoute.Sitemap = [
    { url: BASE, lastModified: now, changeFrequency: "weekly", priority: 1.0 },
    { url: `${BASE}/demo`, lastModified: now, changeFrequency: "weekly", priority: 0.95 },
    { url: `${BASE}/dashboard`, lastModified: now, changeFrequency: "hourly", priority: 0.9 },
    { url: `${BASE}/methodology`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${BASE}/council`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    {
      url: `${BASE}/counter-evidence`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.85,
    },
  ];
  const scenarios = SCENARIOS.map((s) => ({
    url: `${BASE}/demo?scenario=${s}`,
    lastModified: now,
    changeFrequency: "monthly" as const,
    priority: 0.75,
  }));
  const agents = AGENTS.map((a) => ({
    url: `${BASE}/council?agent=${a}`,
    lastModified: now,
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));
  return [...top, ...scenarios, ...agents];
}
