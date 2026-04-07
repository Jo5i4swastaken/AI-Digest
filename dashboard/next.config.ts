import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    typedRoutes: true,
  },
  outputFileTracingIncludes: {
    "app/api/digests/**": ["../digests/archive/**"],
  },
};

export default nextConfig;
