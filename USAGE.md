# AICoreDirector Usage Guide

This guide shows how to actually use AICoreDirector: start services, manage LLMs, register Python plugins and external services, manage prompts, and call the APIs (streaming and batch).

English | 中文: [README_zh-CN.md](README_zh-CN.md)

---

## 1) Start the platform

### Backend (FastAPI)
```bash
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-config log_config.json
```

### Frontend (Vue)
```bash
cd frontend
npm install
npm run dev
```

---

## 2) Manage LLMs (model pool)

Models live in `llm_models.yaml` and can be managed via API.

- List models
```http
GET /api/llm/list
```

- Add a model
```http
POST /api/llm/add
Content-Type: application/json
{
  "name": "gpt-4",
  "url": "https://api.openai.com/v1",
  "key": "sk-xxx",
  "version": "4.0",
  "meta": {"tags": ["llm","openai"], "status": "可用", "qps": 2, "cost": 0.01}
}
```

- Update existing
```http
POST /api/llm/update
{ "name": "gpt-4", "url": "https://api.openai.com/v1", "key": "sk-yyy" }
```

- Delete
```http
POST /api/llm/delete
{ "name": "gpt-4" }
```

- Invoke (non-stream)
```http
POST /llm_invoke
{ "prompt": "Hello", "model_name": "gpt-4", "temperature": 0.7 }
```

- Stream
```http
POST /llm_invoke?stream=true
```
Consume as a streaming response (ReadableStream / iter_content, etc.).

---

## 3) Register a Python plugin

Create `business/your_plugin.py`:
```python
from core.prompt_manager import PromptManager
from core.plugin_loader import plugin_api

@plugin_api
def extract_keywords(text: str):
    pm = PromptManager()
    # prompt = pm.get_prompt("my_prompts", "keywords")
    # TODO: call LLM via adapters if needed
    return {"keywords": ["ai", "governance"]}
```
Restart backend (or rely on hot-reload). The plugin is exposed as:
- Direct: `POST /extract_keywords`
- Unified: `POST /plugin/invoke?plugin_name=extract_keywords`

Example:
```http
POST /plugin/invoke?plugin_name=extract_keywords
{ "payload": {"text": "AICoreDirector is an enterprise AI governance platform."} }
```

### Batch concurrent
```http
POST /plugin/invoke?plugin_name=extract_keywords
{ "batch_payload": [{"text":"doc1"},{"text":"doc2"}] }
```

---

## 4) Register external services (service discovery)

- Register
```http
POST /service-registry/register
{
  "endpoint": "my-ml-endpoint",
  "target_url": "http://localhost:9000",
  "health_check": "/health",
  "desc": "internal model service"
}
```

- Call through AICoreDirector
```http
POST /my-ml-endpoint
{ "text": "hello" }
```

- List
```http
GET /service-discovery/list
```

- Unregister
```http
POST /service-registry/unregister
{ "endpoint": "my-ml-endpoint" }
```

---

## 5) Prompt templates

Store templates under `config_prompts/` (yaml/json/ini).

- List files
```http
GET /api/prompts/list
```

- Get file
```http
GET /api/prompts/file?name=prompt_x.yaml
```

- Save/overwrite
```http
POST /api/prompts/file
{ "name": "prompt_x.yaml", "content": "system: You are a helpful assistant" }
```

- Create new
```http
POST /api/prompts/new
{ "name": "prompt_new.yaml", "content": "system: ..." }
```

In code, use `PromptManager()` to load templates.

---

## 6) Health/QPS/Cost

- `GET /get_model_health` — health & availability
- `GET /get_model_qps` — current QPS per model
- `GET /get_model_hit_count` — selection hit counts
- `GET /get_model_cost` — cost aggregation (and `/get_model_cost_user_app`)

---

## 7) Tips

- Per-session preferred model can be set via `/set_preferred_model` and is honored by plugin/LLM calls.
- Dynamic router records proxied request/response history for observability.
- Batch entry propagates routing context consistently across items.

---

## 8) Production checklist

- Rotate logs, tune per-model `qps`, configure health checks
- Protect public endpoints (gateway/ACL/auth)
- Containerize with `docker-compose.yml` when needed

---

## 9) Links

- API docs (running server): `/docs`, `/openapi.json`
- Frontend dev: `http://localhost:5173/`
- Main README: [README.md](README.md)
- Chinese README: [README_zh-CN.md](README_zh-CN.md)
