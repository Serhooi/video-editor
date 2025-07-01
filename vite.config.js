import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
      '@designcombo/events': path.resolve(__dirname, './events.ts'),
      '@designcombo/state': path.resolve(__dirname, './constants.ts'),
      '@designcombo/timeline': path.resolve(__dirname, './timeline.ts'),
      '@designcombo/types': path.resolve(__dirname, './types.ts'),
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
    rollupOptions: {
      external: [
        // Exclude platform-specific Remotion packages
        '@remotion/compositor-darwin-x64',
        '@remotion/compositor-darwin-arm64',
        '@remotion/compositor-linux-x64',
        '@remotion/compositor-linux-arm64',
        '@remotion/compositor-linux-x64-musl',
        '@remotion/compositor-linux-arm64-musl',
        '@remotion/compositor-linux-x64-gnu',
        '@remotion/compositor-linux-arm64-gnu',
        '@remotion/compositor-win32-x64',
        '@remotion/compositor-windows-x64',
        'esbuild',
      ],
    },
  },
});

