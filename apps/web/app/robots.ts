import type { MetadataRoute } from "next";

/**
 * robots.txt — emitted at /robots.txt. Allow all crawlers, point at
 * the sitemap. The Polymarket proxy and auth routes are explicitly
 * disallowed because they're dynamic API paths, not indexable
 * content.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/signin", "/logout"],
      },
    ],
    sitemap: "https://athean-trades.vercel.app/sitemap.xml",
    host: "https://athean-trades.vercel.app",
  };
}
