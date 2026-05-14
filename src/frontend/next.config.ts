import type { NextConfig } from "next";

const backendOrigin =
  process.env.BACKEND_PROXY_URL?.replace(/\/+$/, "") || "http://backend:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
