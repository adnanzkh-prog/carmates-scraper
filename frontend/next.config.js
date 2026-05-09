/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',           // ← ADD THIS for static site generation
  distDir: 'dist',            // ← ADD THIS (Cloudflare Pages default)
  images: {
    unoptimized: true,        // ← ADD THIS (required for static export)
    domains: ['images.unsplash.com', 'carsales.pxcrush.net', 'gumtree.com.au'],
  },
  // REMOVED: headers() doesn't work with static export
};

module.exports = nextConfig;
