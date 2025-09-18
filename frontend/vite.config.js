import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { getBackendUrl } from './config/backend.js';

export default defineConfig(({ command, mode }) => {
  // 从配置文件获取后端地址 - 只需要在 config/backend.js 中修改一次
  const backendTarget = getBackendUrl();
  
  console.log(`🚀 当前后端服务地址: ${backendTarget}`);
  console.log(`🌍 运行模式: ${command} (${mode})`);

  return {
    plugins: [vue()],
    server: {
      proxy: {
        '/api/readme': {
          target: backendTarget,
          changeOrigin: true,
          rewrite: path => path
        },
        '/api': {
          target: backendTarget, // 后端API服务地址
          changeOrigin: true,
        },
        '/history': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/llm_status': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/list_LLM': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/get_model_health': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/get_model_qps': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/get_model_hit_count': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/get_model_cost': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/service-discovery': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/docs': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/llm_invoke': {
          target: backendTarget,
          changeOrigin: true,
        },
      }
    },
    // 环境变量配置
    define: {
      __BACKEND_URL__: JSON.stringify(backendTarget)
    }
  };
}); 