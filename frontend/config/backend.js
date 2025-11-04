// 后端服务配置管理
// 只需要在这里修改一次后端地址

const config = {
  // 开发环境后端地址
  development: {
    backendUrl: 'http://127.0.0.1:4000',
    apiTimeout: 30000,
    enableProxy: true
  },
  
  // 生产环境后端地址
  production: {
    backendUrl: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:4005',
    apiTimeout: 60000,
    enableProxy: false
  },
  
  // 测试环境后端地址
  test: {
    backendUrl: 'http://test-server:8000',
    apiTimeout: 30000,
    enableProxy: true
  }
};

// 获取当前环境配置
const getConfig = (env = process.env.NODE_ENV || 'development') => {
  return config[env] || config.development;
};

// 导出配置
export default config;
export { getConfig };

// 获取后端URL
export const getBackendUrl = () => {
  return getConfig().backendUrl;
};
