/** @type {import('next').NextConfig} */
const nextConfig = {
  ...(process.env.STANDALONE_BUILD === "1" ? { output: "standalone" } : {}),
  reactStrictMode: true,
  poweredByHeader: false,
};

module.exports = nextConfig;

