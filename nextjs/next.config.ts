import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: { root: __dirname },
  experimental: {
    serverActions: { bodySizeLimit: "120mb" },
    proxyClientMaxBodySize: "120mb",
  },
  outputFileTracingExcludes: {
    "*": ["**/data/**", "**/.processed-v1.cache"],
  },
};

export default nextConfig;
