# 后端配置管理

## 概述

这个配置文件用于集中管理所有与后端服务相关的配置，避免在多个文件中重复配置相同的值。

## 使用方法

### 1. 修改后端地址

当需要修改后端服务地址时，**只需要修改 `config/backend.js` 文件中的一处**：

```javascript
// 在 config/backend.js 中修改
const config = {
  development: {
    backendUrl: 'http://127.0.0.1:8000',  // 修改这里
    // ...
  },
  // ...
};
```

### 2. 环境配置

支持三种环境配置：

- **development**: 开发环境
- **production**: 生产环境  
- **test**: 测试环境

### 3. 在代码中使用

```javascript
import { getBackendUrl, getConfig } from './config/backend.js';

// 获取后端URL
const backendUrl = getBackendUrl();

// 获取完整配置
const config = getConfig();
console.log(config.apiTimeout);
```

## 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `backendUrl` | 后端服务地址 | `http://127.0.0.1:8000` |
| `apiTimeout` | API请求超时时间(ms) | `30000` |
| `enableProxy` | 是否启用代理 | `true` |

## 环境变量

可以通过环境变量覆盖配置：

```bash
# 设置生产环境后端地址
export VITE_BACKEND_URL=https://api.production.com

# 设置环境
export NODE_ENV=production
```

## 优势

✅ **集中管理**: 所有配置在一个文件中  
✅ **一次修改**: 修改后端地址只需要改一处  
✅ **环境支持**: 支持开发、测试、生产环境  
✅ **类型安全**: 配置结构清晰，易于维护  
✅ **灵活配置**: 支持环境变量覆盖  

## 注意事项

1. 修改配置后需要重启开发服务器
2. 生产环境建议使用环境变量配置
3. 测试环境配置需要根据实际测试服务器地址调整



