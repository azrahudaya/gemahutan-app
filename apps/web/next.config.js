/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {},
  },
  async rewrites() {
    // Dev: teruskan /api/* ke API. Di produksi, Caddy yang menangani.
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: "/api/:path*",
          destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
        },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;
