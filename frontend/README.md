# AICoreDirector Web 客户端（前端）

本目录为 AICoreDirector 的 Web 前端项目，基于 Vue 3 + Vite + Element Plus 实现。

## 主要功能
- API 配置与管理
- 实时监控（模型健康、QPS、命中率、成本等）
- 插件生态可视化管理与调用
- 模型列表与状态展示
- 历史调用记录

## 目录结构
- `src/`：前端源码
- `public/`：静态资源
- `README.md`：说明文档

## 启动方式
1. 安装依赖
   ```bash
   cd frontend
   npm install
   ```
2. 启动开发服务器
   ```bash
   npm run dev
   ```

## 说明
- 默认后端 API 地址为 `/api`，可在 `.env` 文件中修改。
- 需配合 AICoreDirector 后端服务一同运行。 