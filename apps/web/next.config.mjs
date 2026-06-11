// @ts-check

// `output: "standalone"` is for self-hosted Docker. Vercel handles output
// for us, and forcing standalone breaks the deploy pipeline there.
const onVercel = !!process.env.VERCEL;

/** @type {import('next').NextConfig} */
const config = {
  output: onVercel ? undefined : "standalone",
  reactStrictMode: true,
  compress: true,
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [
      { protocol: "https", hostname: "images.unsplash.com" },
      { protocol: "https", hostname: "api.iconify.design" },
      { protocol: "https", hostname: "upload.wikimedia.org" },
    ],
  },
  experimental: {
    // Tree-shake icon/animation imports at the module level so only
    // used exports land in the client bundle.
    optimizePackageImports: ["lucide-react", "framer-motion"],
  },
};

export default config;
