import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api/readme': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: path => path
      },
      '/api': {
        target: 'http://localhost:8000', // 后端API服务地址
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, '')
      },
      '/history': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/llm_status': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    }
  }
}); 