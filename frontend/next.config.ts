import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  distDir: process.env.AURA_E2E_BUILD === "1" ? ".next-e2e" : ".next",
  output: process.env.AURA_STANDALONE === "1" ? "standalone" : undefined,
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
      {
        source: "/api/integrations/google/callback",
        headers: [{ key: "Referrer-Policy", value: "no-referrer" }],
      },
    ];
  },
  async rewrites() {
    const privateAddress = process.env.AURA_API_HOSTPORT;
    const backendUrl = (
      (privateAddress ? `http://${privateAddress}` : undefined) ??
      process.env.AURA_API_SERVER_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://127.0.0.1:8000"
    ).replace(/\/+$/, "");

    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
