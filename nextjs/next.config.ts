import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: { root: __dirname },
  experimental: { serverActions: { bodySizeLimit: "120mb" } },
};

export default nextConfig;
