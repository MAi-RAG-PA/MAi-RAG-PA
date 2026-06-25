// ~/MAi-RAG/frontend/vite.config.js //

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
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
});
