import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      '/apicompile': {
        target: 'http://backend:3000',
        changeOrigin: true,
        rewrite: (path) => path, // mantém o path
      },
    },
  },
});
