const nextConfig = {
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || "https://word-territory-ja.onrender.com"
  }
};

module.exports = nextConfig;
