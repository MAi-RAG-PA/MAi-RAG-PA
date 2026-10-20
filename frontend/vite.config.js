// frontend/vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import viteImagemin from 'vite-plugin-imagemin';

export default defineConfig(({ command }) => ({
  plugins: [
    react(),
    viteImagemin({
      gifsicle: { optimizationLevel: 7, interlaced: false },
      optipng: { optimizationLevel: 7 },
      mozjpeg: { quality: 80 },
      pngquant: { quality: [0.65, 0.9], speed: 4 },
      svgo: {
        plugins: [
          { name: 'removeViewBox' },
          { name: 'removeEmptyAttrs', active: false }
        ]
      }
    })
  ],
  // Strip console.* and debugger from PRODUCTION bundles only.
  // (This used to sit inside `build`, where Vite ignores it, so debug logs shipped in dist.
  // Gated on `command` so `npm run dev` keeps console output for troubleshooting.)
  ...(command === 'build' && { esbuild: { drop: ['console', 'debugger'] } }),
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: ['framer-motion', 'lucide-react'],
          utils: ['axios']
        }
      }
    },
    minify: 'esbuild',
    sourcemap: false,
    chunkSizeWarningLimit: 1000
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/notes': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/calendar': 'http://localhost:8000',
      '/voice': 'http://localhost:8000',
      '/system_prompt': 'http://localhost:8000'
    }
  }
}));
