+++

date = '2025-07-31T18:22:48+08:00' 

title = 'AICoreDirector 两级用户体系设计' 

+++

![xx](/docs/TPU流程图.png)

```
![云图片](/docs/TPU流程图.png)
```

![1754016361877](/docs/1754016361877.png)



![aaa](/docs/TPU流程图.png)

# AICoreDirector 两级用户体系设计

## 📋 概述

AICoreDirector 作为企业级AI能力中枢，需要支持不同层级的用户访问和管理。本文档设计了两级用户体系，以满足不同角色的需求。

## 🎯 用户分级

### 1. **管理员 (Admin)**
- **权限范围**：系统级完全管理
- **典型用户**：IT负责人、系统管理员、技术主管
- **主要职责**：
  - 用户账户管理
  - LLM模型配置管理
  - 系统监控和维护
  - 全局数据查看

### 2. **普通用户 (User)**
- **权限范围**：个人使用权限
- **典型用户**：开发工程师、业务人员、客服、市场人员
- **主要职责**：
  - 个人Prompt模板管理
  - 服务调用和测试
  - 个人数据查看

## 📊 权限矩阵

| 功能模块 | Admin | User | 说明 |
|---------|-------|------|------|
| **用户管理** | ✅ 增删改查 | ❌ | 管理员可创建、删除、修改用户账户 |
| **LLM配置** | ✅ 增删改查 | ✅ 查看 | 管理员可配置、管理所有LLM模型 |
| **服务发现** | ✅ 全部 | ✅ 查看 | 所有用户可查看服务列表 |
| **调用历史** | ✅ 全部 | ✅ 个人 | 管理员看全部，用户只看自己的 |
| **成本监控** | ✅ 全部 | ✅ 个人 | 管理员看全局成本，用户看个人成本 |
| **Prompt管理** | ✅ 增删改查所有 | ✅ 增删改自己的，查看所有 | 用户可创建个人模板，查看所有模板 |
| **系统监控** | ✅ 全部 | ❌ | 管理员可查看系统健康状态、QPS等 |

## 🏗️ 技术实现

### 后端权限控制

```python
from enum import Enum
from functools import wraps
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"

class UserManager:
    def __init__(self):
        self.storage = FileStorage()
    
    def get_user(self, user_id: str) -> Optional[dict]:
        data = self.storage.read_json("users.json")
        return data.get("users", {}).get(user_id)
    
    def is_admin(self, user_id: str) -> bool:
        user = self.get_user(user_id)
        return user and user.get("role") == "admin"

# 权限装饰器
def require_admin(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user_id = get_current_user_id(request)
        if not user_manager.is_admin(user_id):
            raise HTTPException(403, "需要管理员权限")
        return await func(request, *args, **kwargs)
    return wrapper

def require_auth(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user_id = get_current_user_id(request)
        if not user_id:
            raise HTTPException(401, "需要登录")
        return await func(request, *args, **kwargs)
    return wrapper

# API接口权限控制
@app.post("/api/llm/add")
@require_admin
async def add_llm(model: dict = Body(...)):
    """添加LLM模型 - 仅管理员"""
    pass

@app.post("/api/llm/delete")
@require_admin
async def delete_llm(model: dict = Body(...)):
    """删除LLM模型 - 仅管理员"""
    pass

@app.get("/api/prompt/list")
@require_auth
async def list_prompts(current_user: dict = Depends(get_current_user)):
    """获取Prompt列表 - 管理员看全部，用户看全部（只读）"""
    if user_manager.is_admin(current_user["id"]):
        prompts = prompt_manager.get_all_prompts()
    else:
        prompts = prompt_manager.get_all_prompts_readonly()
    return {"prompts": prompts}

@app.post("/api/prompt/add")
@require_auth
async def add_prompt(
    name: str,
    content: str,
    current_user: dict = Depends(get_current_user)
):
    """添加Prompt - 管理员可添加任何，用户只能添加自己的"""
    if user_manager.is_admin(current_user["id"]):
        prompt_id = prompt_manager.create_prompt(name, content, None)  # 管理员可创建公共模板
    else:
        prompt_id = prompt_manager.create_prompt(name, content, current_user["id"])
    return {"id": prompt_id, "message": "创建成功"}

@app.delete("/api/prompt/{prompt_id}")
@require_auth
async def delete_prompt(
    prompt_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除Prompt - 管理员可删除任何，用户只能删除自己的"""
    prompt = prompt_manager.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt不存在")
    
    if not user_manager.is_admin(current_user["id"]) and prompt["user_id"] != current_user["id"]:
        raise HTTPException(403, "只能删除自己的Prompt")
    
    prompt_manager.delete_prompt(prompt_id)
    return {"message": "删除成功"}
```

### 前端权限控制

```javascript
// 权限配置
const PERMISSIONS = {
  ADMIN: ['*'],  // 管理员拥有所有权限
  USER: ['history', 'prompt_manage', 'service_call', 'cost_view']
}

// 权限检查函数
function hasPermission(permission) {
  const userRole = userStore.role
  return PERMISSIONS[userRole].includes('*') || 
         PERMISSIONS[userRole].includes(permission)
}

// 用户状态管理
const userStore = reactive({
  id: null,
  username: '',
  role: 'user',
  isAuthenticated: false
})

// 菜单权限控制
const menuItems = computed(() => {
  const items = [
    { name: 'LLM监控', key: 'dashboard', permission: 'cost_view' },
    { name: '服务发现', key: 'discovery', permission: 'service_discovery' },
    { name: '调用历史', key: 'history', permission: 'history' },
    { name: 'LLM配置', key: 'llmconfig', permission: 'llm_config' },
    { name: 'Prompt管理', key: 'prompt', permission: 'prompt_manage' },
    { name: '帮助', key: 'help', permission: '*' }
  ]
  
  return items.filter(item => hasPermission(item.permission))
})

// Prompt管理组件权限控制
const PromptManager = {
  setup() {
    const userRole = userStore.role
    const isAdmin = userRole === 'ADMIN'
    
    // 检查是否可以编辑Prompt
    const canEdit = (prompt) => {
      return isAdmin || prompt.user_id === userStore.id
    }
    
    // 检查是否可以删除Prompt
    const canDelete = (prompt) => {
      return isAdmin || prompt.user_id === userStore.id
    }
    
    // 检查是否可以创建Prompt
    const canCreate = () => {
      return true  // 所有用户都可以创建
    }
    
    return { canEdit, canDelete, canCreate }
  }
}
```

## 💾 数据存储方案

### 轻量级JSON文件存储

```python
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import threading

class FileStorage:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.lock = threading.Lock()
        os.makedirs(data_dir, exist_ok=True)
        
    def _get_file_path(self, filename: str) -> str:
        return os.path.join(self.data_dir, filename)
    
    def read_json(self, filename: str) -> dict:
        file_path = self._get_file_path(filename)
        if not os.path.exists(file_path):
            return {}
        
        with self.lock:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def write_json(self, filename: str, data: dict):
        file_path = self._get_file_path(filename)
        with self.lock:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

class UserManager:
    def __init__(self):
        self.storage = FileStorage()
    
    def get_user(self, user_id: str) -> Optional[dict]:
        data = self.storage.read_json("users.json")
        return data.get("users", {}).get(user_id)
    
    def create_user(self, user_id: str, username: str, role: str = "user"):
        data = self.storage.read_json("users.json")
        if "users" not in data:
            data["users"] = {}
        
        data["users"][user_id] = {
            "id": user_id,
            "username": username,
            "role": role,
            "created_at": datetime.now().isoformat()
        }
        
        self.storage.write_json("users.json", data)
    
    def is_admin(self, user_id: str) -> bool:
        user = self.get_user(user_id)
        return user and user.get("role") == "admin"

class UserPromptManager:
    def __init__(self):
        self.storage = FileStorage()
        self.prompt_dir = "config_prompts"  # 使用现有Prompt目录
    
    def get_user_prompts(self, user_id: str) -> dict:
        """获取用户的Prompt关联信息"""
        data = self.storage.read_json("user_prompts.json")
        return data.get("user_prompts", {}).get(user_id, {
            "owned_prompts": [],
            "favorite_prompts": [],
            "created_at": datetime.now().isoformat()
        })
    
    def get_user_accessible_prompts(self, user_id: str) -> List[str]:
        """获取用户可访问的Prompt文件名列表"""
        user_prompts = self.get_user_prompts(user_id)
        
        # 获取所有Prompt文件
        all_prompts = []
        for fname in os.listdir(self.prompt_dir):
            if os.path.isfile(os.path.join(self.prompt_dir, fname)):
                all_prompts.append(fname)
        
        # 用户可以看到所有Prompt文件（只读）
        return all_prompts
    
    def can_user_edit_prompt(self, user_id: str, prompt_filename: str) -> bool:
        """检查用户是否可以编辑指定Prompt文件"""
        user_prompts = self.get_user_prompts(user_id)
        return prompt_filename in user_prompts["owned_prompts"]
    
    def add_user_prompt(self, user_id: str, prompt_filename: str, prompt_type: str = "owned"):
        """为用户添加Prompt关联"""
        data = self.storage.read_json("user_prompts.json")
        if "user_prompts" not in data:
            data["user_prompts"] = {}
        
        if user_id not in data["user_prompts"]:
            data["user_prompts"][user_id] = {
                "owned_prompts": [],
                "favorite_prompts": [],
                "created_at": datetime.now().isoformat()
            }
        
        if prompt_type == "owned":
            if prompt_filename not in data["user_prompts"][user_id]["owned_prompts"]:
                data["user_prompts"][user_id]["owned_prompts"].append(prompt_filename)
        elif prompt_type == "favorite":
            if prompt_filename not in data["user_prompts"][user_id]["favorite_prompts"]:
                data["user_prompts"][user_id]["favorite_prompts"].append(prompt_filename)
        
        self.storage.write_json("user_prompts.json", data)
    
    def remove_user_prompt(self, user_id: str, prompt_filename: str, prompt_type: str = "owned"):
        """移除用户的Prompt关联"""
        data = self.storage.read_json("user_prompts.json")
        if user_id in data.get("user_prompts", {}):
            if prompt_type == "owned":
                data["user_prompts"][user_id]["owned_prompts"] = [
                    p for p in data["user_prompts"][user_id]["owned_prompts"] 
                    if p != prompt_filename
                ]
            elif prompt_type == "favorite":
                data["user_prompts"][user_id]["favorite_prompts"] = [
                    p for p in data["user_prompts"][user_id]["favorite_prompts"] 
                    if p != prompt_filename
                ]
            self.storage.write_json("user_prompts.json", data)

# 保持现有PromptManager不变，用于兼容现有系统
class PromptManager:
    def __init__(self, prompt_dir="config_prompts"):
        self.prompts = {}
        if not os.path.exists(prompt_dir):
            return
        for fname in os.listdir(prompt_dir):
            fpath = os.path.join(prompt_dir, fname)
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                with open(fpath, "r", encoding="utf-8") as f:
                    self.prompts[fname[:-5]] = yaml.safe_load(f)
            elif fname.endswith(".json"):
                with open(fpath, "r", encoding="utf-8") as f:
                    self.prompts[fname[:-5]] = json.load(f)
            elif fname.endswith(".ini"):
                cp = configparser.ConfigParser()
                cp.read(fpath, encoding="utf-8")
                self.prompts[fname[:-4]] = {s: dict(cp.items(s)) for s in cp.sections()}
    
    def get_prompt(self, plugin, template="default"):
        # plugin: 文件名（不含扩展名），template: section/key
        p = self.prompts.get(plugin, {})
        if isinstance(p, dict):
            return p.get(template, "")
        return p
```

### 数据文件结构

```
data/
├── users.json              # 用户数据
├── user_prompts.json       # 用户与Prompt的关联关系
├── history.json            # 调用历史
└── llm_config.json         # LLM配置

config_prompts/             # 现有Prompt模板存储目录（保持不变）
├── prompt.ini              # 现有Prompt文件
├── prom                    # 现有Prompt文件
├── prompt_x.ini            # 现有Prompt文件
└── ...                     # 其他现有Prompt文件
```

#### users.json 示例
```json
{
  "users": {
    "admin1": {
      "id": "admin1",
      "username": "系统管理员",
      "role": "admin",
      "created_at": "2025-07-01T10:00:00Z"
    },
    "user1": {
      "id": "user1",
      "username": "张三",
      "role": "user",
      "created_at": "2025-07-01T11:00:00Z"
    }
  }
}
```

#### user_prompts.json 示例
```json
{
  "user_prompts": {
    "user1": {
      "owned_prompts": ["prompt.ini", "custom_prompt.yaml"],
      "favorite_prompts": ["prompt.ini"],
      "created_at": "2025-07-01T10:00:00Z"
    },
    "user2": {
      "owned_prompts": ["my_prompt.json"],
      "favorite_prompts": ["prompt.ini", "prompt_x.ini"],
      "created_at": "2025-07-01T11:00:00Z"
    }
  }
}
```

## 🔐 认证机制

### 简化认证方案

```python
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

def get_current_user(token: str = Depends(security)):
    # 简化处理：token直接作为user_id
    # 实际项目中应使用JWT或其他认证方式
    user_id = token.credentials
    user = user_manager.get_user(user_id)
    if not user:
        raise HTTPException(401, "用户不存在")
    return user

# 登录接口
@app.post("/api/login")
async def login(username: str, password: str):
    # 简化处理：直接返回用户信息
    # 实际项目中需要验证密码
    user = user_manager.get_user_by_username(username)
    if not user:
        raise HTTPException(401, "用户名或密码错误")
    
    return {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "token": user["id"]  # 简化处理
    }

# Prompt管理API接口
@app.get("/api/prompt/list")
@require_auth
async def list_prompts(current_user: dict = Depends(get_current_user)):
    """获取Prompt列表 - 兼容现有系统"""
    user_prompt_manager = UserPromptManager()
    
    if user_manager.is_admin(current_user["id"]):
        # 管理员看到所有Prompt文件
        prompt_files = user_prompt_manager.get_user_accessible_prompts(current_user["id"])
    else:
        # 普通用户看到所有Prompt文件（只读）
        prompt_files = user_prompt_manager.get_user_accessible_prompts(current_user["id"])
    
    # 返回文件名列表，兼容现有API
    return {"files": prompt_files}

@app.post("/api/prompt/new")
@require_auth
async def new_prompt_file(
    name: str = Body(...),
    content: str = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """创建新Prompt文件"""
    user_prompt_manager = UserPromptManager()
    
    # 检查文件是否已存在
    file_path = os.path.join("config_prompts", name)
    if os.path.exists(file_path):
        raise HTTPException(409, "文件已存在")
    
    # 创建文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 将文件关联到用户
    user_prompt_manager.add_user_prompt(current_user["id"], name, "owned")
    
    return {"status": "created", "name": name}

@app.post("/api/prompt/file")
@require_auth
async def save_prompt_file(
    name: str = Body(...),
    content: str = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """保存Prompt文件 - 只能编辑自己的文件"""
    user_prompt_manager = UserPromptManager()
    
    if not user_manager.is_admin(current_user["id"]):
        if not user_prompt_manager.can_user_edit_prompt(current_user["id"], name):
            raise HTTPException(403, "只能编辑自己的Prompt文件")
    
    # 保存文件
    file_path = os.path.join("config_prompts", name)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return {"status": "success", "name": name}

@app.post("/api/prompt/favorite/{prompt_filename}")
@require_auth
async def favorite_prompt(
    prompt_filename: str,
    current_user: dict = Depends(get_current_user)
):
    """收藏Prompt文件"""
    user_prompt_manager = UserPromptManager()
    user_prompt_manager.add_user_prompt(current_user["id"], prompt_filename, "favorite")
    return {"message": "收藏成功"}

@app.delete("/api/prompt/{prompt_filename}")
@require_auth
async def delete_prompt(
    prompt_filename: str,
    current_user: dict = Depends(get_current_user)
):
    """删除Prompt文件 - 只能删除自己拥有的"""
    user_prompt_manager = UserPromptManager()
    user_prompts = user_prompt_manager.get_user_prompts(current_user["id"])
    
    if prompt_filename not in user_prompts["owned_prompts"]:
        raise HTTPException(403, "只能删除自己的Prompt文件")
    
    # 删除文件
    file_path = os.path.join("config_prompts", prompt_filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # 移除用户关联
    user_prompt_manager.remove_user_prompt(current_user["id"], prompt_filename, "owned")
    
    return {"message": "删除成功"}
```

## 📱 前端界面适配

### 用户角色显示

```vue
<template>
  <div class="user-info">
    <span>{{ userStore.username }}</span>
    <el-tag :type="userStore.role === 'admin' ? 'danger' : 'primary'">
      {{ userStore.role === 'admin' ? '管理员' : '用户' }}
    </el-tag>
  </div>
</template>
```

### 权限控制组件

```vue
<template>
  <div>
    <!-- 只有管理员可见 -->
    <div v-if="hasPermission('user_manage')">
      <el-button @click="manageUsers">用户管理</el-button>
    </div>
    
    <!-- 所有用户可见 -->
    <div v-if="hasPermission('prompt_manage')">
      <el-button @click="createPrompt">创建Prompt</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const hasPermission = (permission) => {
  return userStore.hasPermission(permission)
}
</script>
```

## 🚀 部署和配置

### 初始化脚本

```python
# init_users.py
from user_manager import UserManager

def init_default_users():
    user_manager = UserManager()
    
    # 创建默认管理员
    user_manager.create_user(
        user_id="admin",
        username="系统管理员",
        role="admin"
    )
    
    # 创建默认用户
    user_manager.create_user(
        user_id="user1",
        username="测试用户",
        role="user"
    )
    
    print("默认用户创建完成")

if __name__ == "__main__":
    init_default_users()
```

### 配置文件

```python
# config.py
class Config:
    # 数据存储路径
    DATA_DIR = "data"
    
    # 默认用户角色
    DEFAULT_USER_ROLE = "user"
    
    # 权限配置
    PERMISSIONS = {
        "admin": ["*"],
        "user": ["history", "prompt_manage", "service_call", "cost_view"]
    }
```

## 📈 升级路径

### 当前方案优势
- **简单易用**：两级权限，逻辑清晰
- **快速部署**：JSON文件存储，零依赖
- **成本低廉**：无需数据库，维护简单
- **易于扩展**：为后续升级预留空间
- **完全兼容**：保持现有Prompt存储方式不变

### 未来升级方向
```
当前：JSON文件 + 两级权限 + 现有Prompt存储
  ↓
中期：SQLite + 三级权限（增加开发者角色）
  ↓
长期：MySQL + 四级权限（完整企业级权限体系）
```

### 兼容性说明
- **现有Prompt系统**：完全保持不变，继续使用 `config_prompts/` 目录
- **用户权限管理**：通过 `user_prompts.json` 管理用户与Prompt的关联关系
- **API接口**：兼容现有的Prompt API，同时增加权限控制
- **业务逻辑**：现有业务代码无需修改，权限控制在API层实现

## ✅ 实施检查清单

### 后端开发
- [ ] 实现FileStorage类
- [ ] 实现UserManager类
- [ ] 实现UserPromptManager类（新增）
- [ ] 保持现有PromptManager类不变
- [ ] 添加权限装饰器
- [ ] 修改API接口支持权限控制
- [ ] 实现认证机制
- [ ] 确保与现有Prompt API兼容

### 前端开发
- [ ] 实现用户状态管理
- [ ] 添加权限检查函数
- [ ] 修改菜单显示逻辑
- [ ] 适配Prompt管理界面
- [ ] 添加用户角色显示

### 测试验证
- [ ] 管理员权限测试
- [ ] 普通用户权限测试
- [ ] Prompt管理功能测试
- [ ] 数据隔离测试
- [ ] 权限升级测试
- [ ] 现有Prompt系统兼容性测试
- [ ] 用户Prompt关联关系测试

---

**文档版本**：v1.0  
**创建时间**：2025年7月  
**适用场景**：小型企业（< 50人）  
**技术栈**：FastAPI + Vue.js + JSON文件存储 