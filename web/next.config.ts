import type { NextConfig } from "next";

const apiOrigin = process.env.TRIBUTARY_API_ORIGIN;

const nextConfig: NextConfig = {
  async rewrites() {
    if (!apiOrigin) {
      return [];
    }

    return [
      {
        source: "/api/upload",
        destination: `${apiOrigin}/api/upload`,
      },
      {
        source: "/api/process",
        destination: `${apiOrigin}/api/process`,
      },
    ];
  },
};

export default nextConfig;
