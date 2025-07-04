const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Убираем standalone для Vercel
  // output: 'standalone', // Только для Docker
  
  // Отключаем TypeScript ошибки для быстрого деплоя
  typescript: {
    ignoreBuildErrors: true,
  },
  
  // Отключаем ESLint ошибки
  eslint: {
    ignoreDuringBuilds: true,
  },
  
  webpack: (config, { isServer }) => {
    // Handle platform-specific Remotion packages
    config.resolve = {
      ...config.resolve,
      fallback: {
        ...config.resolve?.fallback,
        // Darwin (macOS)
        "@remotion/compositor-darwin-x64": false,
        "@remotion/compositor-darwin-arm64": false,
        // Linux
        "@remotion/compositor-linux-x64": false,
        "@remotion/compositor-linux-arm64": false,
        "@remotion/compositor-linux-x64-musl": false,
        "@remotion/compositor-linux-arm64-musl": false,
        "@remotion/compositor-linux-x64-gnu": false,
        "@remotion/compositor-linux-arm64-gnu": false,
        // Windows
        "@remotion/compositor-win32-x64": false,
        "@remotion/compositor-windows-x64": false,
        // Handle esbuild
        esbuild: false,
      },
      // Add explicit path aliases
      alias: {
        ...config.resolve?.alias,
        '@': path.resolve(__dirname),
        '@/hooks': path.resolve(__dirname, './hooks'),
        '@/lib': path.resolve(__dirname, './lib'),
        '@/components': path.resolve(__dirname, './components'),
        '@/app': path.resolve(__dirname, './app'),
        '@/public': path.resolve(__dirname, './public'),
      }
    };
    
    // Add esbuild to external modules
    if (isServer) {
      config.externals = [...config.externals, "esbuild"];
    }
    
    return config;
  },
  
  experimental: {
    serverComponentsExternalPackages: [
      "@remotion/bundler",
      "@remotion/renderer",
      "esbuild",
    ],
  },
};

module.exports = nextConfig;

