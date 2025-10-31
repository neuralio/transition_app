import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone', // Required for Docker deployment

  // Skip linting and type checking during Docker build (faster builds)
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },

  // Disable automatic static optimization to ensure proper server rendering
  experimental: {
    // Force port 3000, no fallback
    serverActions: {
      allowedOrigins: ['localhost:3000']
    }
  }
};

export default nextConfig;
