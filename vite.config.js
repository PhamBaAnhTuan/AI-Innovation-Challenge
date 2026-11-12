import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/admin': 'http://127.0.0.1:8000',
      '/admin.css': 'http://127.0.0.1:8000',
      '/admin.js': 'http://127.0.0.1:8000'
    }
  }
});
