from fastapi import FastAPI, Request, Response, Cookie, Query, Body
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional
import uuid
import os
from dotenv import set_key, unset_key, find_dotenv, dotenv_values
from business.doc_extractor import extract_info_with_history, extract_info, llm
from core.state_manager import state_manager
from core.plugin_loader import get_plugin_func, plugin_registry, scan_and_register_plugins, get_plugin_scan_interval
import traceback
import httpx
from datetime import datetime
import threading
import time
from core.health_checker import QPSMonitor, HealthChecker
from core.model_router import ModelRouter
from filelock import FileLock
import json
import inspect
import asyncio
from adapters.llm_adapter import MultiLLM, llm_context
# 统计功能已移至 core.statistics 模块的函数调用
from api import prompt_api
import yaml
import re
import requests
import contextvars

app = FastAPI()
# 基础目录（项目根目录）
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件服务，用于提供docs目录下的图片等资源
try:
    app.mount("/docs", StaticFiles(directory="docs"), name="docs")
except Exception as e:
    print(f"Warning: Could not mount docs directory: {e}")

app.include_router(prompt_api.router, prefix="/api")
app.include_router(prompt_api.router)

SESSION_COOKIE_NAME = "session_id"

# 全局监控器实例
qps_monitor = QPSMonitor()
health_checker = None  # 启动时初始化

router = ModelRouter(lambda: llm_manager.models)

SERVICE_REGISTRY_FILE = "service_registry.json"
SERVICE_REGISTRY_LOCK = "service_registry.json.lock"

# 插件批量并发调度开关
PLUGINS_BATCH_DISPATCH_ENABLED = True  # 设为False可一键禁用该逻辑

# 全局 LLM 实例（假设只初始化一次）
llm_manager: MultiLLM = None

LLM_YAML_PATH = 'llm_models.yaml'

# --- Language negotiation (i18n) ---
SUPPORTED_LOCALES = {"zh-CN", "en"}

def negotiate_locale(request: Request) -> str:
    # Priority: explicit query param > header > default
    lang = request.query_params.get("lang")
    if lang in SUPPORTED_LOCALES:
        return lang
    # Accept-Language parsing (simple)
    accept_lang = request.headers.get("Accept-Language", "").lower()
    if accept_lang.startswith("zh"):
        return "zh-CN"
    if accept_lang.startswith("en"):
        return "en"
    return "zh-CN"

@app.middleware("http")
async def language_negotiation(request: Request, call_next):
    try:
        request.state.locale = negotiate_locale(request)
    except Exception:
        request.state.locale = "zh-CN"
    response = await call_next(request)
    try:
        response.headers["Content-Language"] = getattr(request.state, "locale", "zh-CN")
    except Exception:
        pass
    return response

def save_service_registry(service_registry):
    with FileLock(SERVICE_REGISTRY_LOCK):
        with open(SERVICE_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(service_registry, f, ensure_ascii=False, indent=2)

def load_service_registry():
    if os.path.exists(SERVICE_REGISTRY_FILE):
        with FileLock(SERVICE_REGISTRY_LOCK):
            with open(SERVICE_REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}

service_registry = load_service_registry()

# 恢复Pydantic数据模型类
class SetPreferredModelRequest(BaseModel):
    model_name: str
    model_url: str | None = None
    model_key: str | None = None

class LLMInvokeRequest(BaseModel):
    prompt: str
    model_name: str | None = None
    tags: list[str] | None = None
    biz_level: str | None = None
    prefer_cost: str | None = None
    user_id: str | None = None
    app_id: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: list[str] | None = None

class ManageLLMRequest(BaseModel):
    action: Literal['add', 'update', 'delete']
    model_name: str
    base_url: str | None = None
    api_key: str | None = None
    tags: list[str] | None = None
    version: str | None = None
    status: str | None = None
    cost: float | None = None
    qps: float | None = None
    health: str | None = None

# 新增：服务健康状态自动感知定时任务
SERVICE_HEALTH_CHECK_INTERVAL = 60  # 秒

def check_service_health(endpoint, info):
    health_check = info.get("health_check")
    status = "unknown"
    if health_check:
        try:
            if health_check.startswith("http://") or health_check.startswith("https://"):
                url = health_check
            else:
                base_url = info.get("target_url")
                if base_url:
                    url = base_url.rstrip("/") + "/" + health_check.lstrip("/")
                else:
                    url = health_check
            resp = requests.get(url, timeout=10)
            status = "available" if resp.status_code == 200 else "offline"
        except Exception:
            status = "offline"
    else:
        status = "unknown"
    return status

def update_all_service_status():
    changed = False
    for endpoint, info in service_registry.items():
        new_status = check_service_health(endpoint, info)
        if info.get("status") != new_status:
            info["status"] = new_status
            changed = True
    if changed:
        save_service_registry(service_registry)

def start_service_health_monitor():
    def monitor_loop():
        while True:
            update_all_service_status()
            time.sleep(SERVICE_HEALTH_CHECK_INTERVAL)
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()

def get_now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.post("/service-registry/register")
async def register_service(service_data: dict):
    # 兼容description字段
    if "description" in service_data and not service_data.get("desc"):
        service_data["desc"] = service_data["description"]
    status = check_service_health(service_data["endpoint"], service_data)
    service_data["status"] = status
    service_data["last_update_time"] = get_now_str()
    service_registry[service_data["endpoint"]] = service_data
    save_service_registry(service_registry)
    return {"status": "success", "registered_endpoint": service_data["endpoint"], "health_status": status}

# 启动时自动开启健康监控
@app.on_event("startup")
def on_startup():
    scan_and_register_plugins(app)
    move_dynamic_router_to_end(app)
    start_plugin_hot_reload(app)
    init_llm_manager()  # 先初始化LLM管理器
    start_health_checker()  # 再启动健康检查器
    start_service_health_monitor()  # 新增：启动服务健康监控

@app.post("/set_preferred_model")
async def set_preferred_model(request: Request, response: Response, preferred_model_info: SetPreferredModelRequest, session_id: str = Cookie(None)):
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(key=SESSION_COOKIE_NAME, value=session_id)
    model_name_to_find = preferred_model_info.model_name
    preferred_index = -1
    global llm_manager
    for i, model in enumerate(llm_manager.models):
        if model["name"] == model_name_to_find:
            preferred_index = i
            break
    if preferred_index != -1:
        state_manager.set_preferred_model_index(session_id, preferred_index)
        try:
            model_info = llm_manager.models[preferred_index]
            # 同步客户端已经预先创建，异步客户端按需创建
            if model_info.get("sync_client") is None:
                print(f"[api:/set_preferred_model] 警告: 模型 {model_name_to_find} 的同步客户端未正确初始化", flush=True)
            # 异步客户端按需创建，这里不检查
        except Exception as e:
            print(f"[api:/set_preferred_model] Could not verify client: {e}", flush=True)
        return JSONResponse(content={
            "message": f"Preferred model set to {model_name_to_find} for session {session_id}.",
            "preferred_model_index": preferred_index,
            "session_id": session_id
        })
    else:
        return JSONResponse(content={
            "message": f"Model {model_name_to_find} not found in configured models.",
            "available_models": [m["name"] for m in llm_manager.models],
            "session_id": session_id
        }, status_code=404)

def llm_stream_generator(prompt, model_name, temperature=None, top_p=None, max_tokens=None, stop=None, user_id=None, app_id=None):
    global llm_manager
    # 如果llm有原生流式方法，优先用
    if hasattr(llm_manager, 'generate_stream_with_specific_model'):
        yield from llm_manager.generate_stream_with_specific_model(
            prompt=prompt,
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop
        )
    else:
        # 兼容：一次性返回全部内容
        result_obj = llm_manager.generate_with_specific_model(
            prompt=prompt,
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop
        )
        # 只记录用户应用维度的成本统计，避免重复记录
        from core.statistics import record_model_cost_user_app
        record_model_cost_user_app(model_name, user_id, app_id, result_obj.get("cost") or 0.0)
        yield result_obj.get("result")

@app.post("/llm_invoke")
async def LLM_invoke(request: LLMInvokeRequest, stream: bool = Query(False)):
    print(f"[LLM_invoke] 收到请求: prompt='{request.prompt[:50]}...', model_name='{request.model_name}', stream={stream}")
    # --- 自动设置 LLM 路由上下文 ---
    llm_context.set(request.dict())
    prompt = request.prompt
    model_name = request.model_name
    tags = request.tags
    biz_level = request.biz_level
    prefer_cost = request.prefer_cost
    user_id = request.user_id
    app_id = request.app_id
    temperature = request.temperature
    top_p = request.top_p
    max_tokens = request.max_tokens
    stop = request.stop
    used_model = None
    try:
        global llm_manager
        if model_name:
            idx = next((i for i, m in enumerate(llm_manager.models) if m["name"] == model_name), None)
            if idx is not None:
                model = llm_manager.models[idx]
                if qps_monitor.is_limited(model_name, model.get("qps", 0)):
                    return JSONResponse(content={"error": "QPS limit exceeded for model", "model": model_name}, status_code=429)
                qps_monitor.record(model_name)
                if health_checker:
                    health_checker.notify_model_active(model_name)
        else:
            try:
                model = router.select_model(tags=tags, biz_level=biz_level, prefer_cost=prefer_cost)
            except Exception as e:
                return JSONResponse(content={"error": str(e)}, status_code=404)
            model_name = model["name"]
            if qps_monitor.is_limited(model_name, model.get("qps", 0)):
                return JSONResponse(content={"error": "QPS limit exceeded for model", "model": model_name}, status_code=429)
            qps_monitor.record(model_name)
            if health_checker:
                health_checker.notify_model_active(model_name)
        # 成本统计初始化（已移至新的统计系统）
        if stream:
            def stream_gen():
                yield from llm_stream_generator(
                    prompt=prompt,
                    model_name=model_name,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    stop=stop,
                    user_id=user_id,
                    app_id=app_id
                )
            return StreamingResponse(stream_gen(), media_type="text/plain")
        # 非流式同步返回
        result_obj = llm_manager.generate_with_specific_model(
            prompt=prompt,
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop
        )
        used_model = model_name
        # 只记录用户应用维度的成本统计，避免重复记录
        from core.statistics import record_model_cost_user_app
        record_model_cost_user_app(model_name, user_id, app_id, result_obj.get("cost") or 0.0)
        return JSONResponse(content={
            "result": result_obj.get("result"),
            "used_model": used_model,
            "token_usage": result_obj.get("token_usage"),
            "cost": result_obj.get("cost"),
            "user_id": user_id,
            "app_id": app_id
        })
    except ValueError as e:
        return JSONResponse(
            content={
                "error": str(e),
                "available_models": [m["name"] for m in llm_manager.models],
            },
            status_code=404,
        )
    except Exception as e:
        return JSONResponse(
            content={"error": "Model invocation failed", "details": str(e)},
            status_code=500,
        )

@app.post("/manage_LLM")
async def manage_LLM(request: ManageLLMRequest):
    dotenv_path = find_dotenv()
    if not dotenv_path:
        with open(".env", "w") as f:
            pass
        dotenv_path = find_dotenv()
    action = request.action
    model_name = request.model_name
    base_url = request.base_url
    api_key = request.api_key
    tags = getattr(request, 'tags', None)
    version = getattr(request, 'version', None)
    status = getattr(request, 'status', None)
    cost = getattr(request, 'cost', None)
    qps = getattr(request, 'qps', None)
    health = getattr(request, 'health', None)
    if action in ['add', 'update']:
        if not (base_url and api_key):
            return JSONResponse(status_code=400, content={"error": "base_url and api_key are required for add/update actions."})
    global llm_manager
    if action == 'add':
        if not llm_manager.add_LLM(model_name, base_url, api_key, tags, version, status, cost, qps, health):
            return JSONResponse(status_code=409, content={"error": f"Model '{model_name}' already exists in memory."})
        idx = 0
        while os.environ.get(f"MODEL_NAME_{idx}"):
            idx += 1
        set_key(dotenv_path, f"MODEL_NAME_{idx}", model_name)
        set_key(dotenv_path, f"BASE_URL_{idx}", base_url)
        set_key(dotenv_path, f"API_KEY_{idx}", api_key)
        set_key(dotenv_path, f"TAGS_{idx}", ",".join(tags) if tags else "")
        set_key(dotenv_path, f"VERSION_{idx}", version or "")
        set_key(dotenv_path, f"STATUS_{idx}", status or "available")
        set_key(dotenv_path, f"COST_{idx}", str(cost) if cost is not None else "0.0")
        set_key(dotenv_path, f"QPS_{idx}", str(qps) if qps is not None else "0")
        set_key(dotenv_path, f"HEALTH_{idx}", health or "unknown")
        return {"status": "success", "message": f"Model '{model_name}' added and persisted at index {idx}."}
    elif action == 'update':
        if not llm_manager.update_LLM(model_name, base_url, api_key):
            return JSONResponse(status_code=404, content={"error": f"Model '{model_name}' not found in memory."})
        env_vars = dotenv_values(dotenv_path)
        found_idx = -1
        for key, name in env_vars.items():
            if key.startswith("MODEL_NAME_") and name == model_name:
                found_idx = key.split('_')[-1]
                break
        if found_idx != -1:
            set_key(dotenv_path, f"BASE_URL_{found_idx}", base_url)
            set_key(dotenv_path, f"API_KEY_{found_idx}", api_key)
            return {"status": "success", "message": f"Model '{model_name}' updated and persisted."}
        else:
            return JSONResponse(status_code=404, content={"error": f"Model '{model_name}' not found in .env file for persistence."})
    elif action == 'delete':
        env_vars = dotenv_values(dotenv_path)
        found_idx = -1
        for key, name in env_vars.items():
            if key.startswith("MODEL_NAME_") and name == model_name:
                found_idx = key.split('_')[-1]
                break
        if not llm_manager.remove_LLM(model_name):
            return JSONResponse(status_code=404, content={"error": f"Model '{model_name}' not found in memory."})
        if found_idx != -1:
            unset_key(dotenv_path, f"MODEL_NAME_{found_idx}")
            unset_key(dotenv_path, f"BASE_URL_{found_idx}")
            unset_key(dotenv_path, f"API_KEY_{found_idx}")
            return {"status": "success", "message": f"Model '{model_name}' removed from memory and .env."}
        else:
            return JSONResponse(status_code=404, content={"error": f"Model '{model_name}' was removed from memory but not found in .env for persistence."})

@app.post("/list_LLM")
async def list_LLM():
    global llm_manager
    result = []
    for model in llm_manager.models:
        meta = model.get('meta', {})
        result.append({
            "name": model["name"],
            "url": model["url"],
            "version": model.get("version", ""),
            "tags": meta.get("tags", []),
            "status": meta.get("status", "available"),
            "qps": meta.get("qps", 0),
            "cost": meta.get("cost", 0.0),
            "index": llm_manager.models.index(model),
            "health": model.get("health", "unknown"),
            "current_global_model_index": llm_manager.current,
            "current_global_model_name": llm_manager.models[llm_manager.current]["name"] if llm_manager.models else None,
            "meta": meta  # 新增：完整元数据
        })
    return {"models": result}

@app.get("/get-openapi-schema")
async def get_openapi_schema():
    return JSONResponse(content=app.openapi())

@app.post("/service-registry/unregister")
async def unregister_service(service_data: dict):
    endpoint = service_data["endpoint"]
    if endpoint in service_registry:
        del service_registry[endpoint]
        save_service_registry(service_registry)
        return {"status": "success", "unregistered_endpoint": endpoint}
    return {"status": "error", "message": "Endpoint not found"}

for func_name, (func, module_name) in plugin_registry.items():
    route_path = f"/{func_name}"
    if route_path not in [route.path for route in app.routes]:
        app.add_api_route(route_path, get_plugin_func(func, module_name, func_name), methods=["GET", "POST"])

def move_dynamic_router_to_end(app):
    for i, route in enumerate(app.router.routes):
        if getattr(route, 'path', None) == "/{path:path}":
            app.router.routes.append(app.router.routes.pop(i))
            break

# 移除重复的启动事件，统一在第一个启动事件中处理

def start_plugin_hot_reload(app, interval=None):
    if interval is None:
        interval = get_plugin_scan_interval()
    plugin_dir = "business"
    last_dir_mtime = None
    def reload_loop():
        nonlocal last_dir_mtime
        while True:
            try:
                current_mtime = os.path.getmtime(plugin_dir)
                if last_dir_mtime is None or current_mtime != last_dir_mtime:
                    scan_and_register_plugins(app)
                    last_dir_mtime = current_mtime
            except Exception as e:
                print(f"[PluginHotReload] Error: {e}")
            time.sleep(interval)
    t = threading.Thread(target=reload_loop, daemon=True)
    t.start()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def dynamic_router(request: Request, path: str):
    print(f"[dynamic_router] 收到请求: {request.method} /{path}", flush=True)
    print(f"[dynamic_router] service_registry keys: {list(service_registry.keys())}", flush=True)
    
    # 排除 /api 路径，让它们由其他路由处理
    if path.startswith("api/"):
        print(f"[dynamic_router] 跳过 /api 路径: {path}", flush=True)
        return JSONResponse(content={"error": "API path not handled by dynamic router"}, status_code=404)
    
    # 排除 /prompts 路径，让它们由 prompt_api 处理
    if path.startswith("prompts/"):
        print(f"[dynamic_router] 跳过 /prompts 路径: {path}", flush=True)
        return JSONResponse(content={"error": "Prompts path not handled by dynamic router"}, status_code=404)
    
    if path in service_registry:
        service_info = service_registry[path]
        target_url = service_info["target_url"].rstrip("/")
        url = f"{target_url}/{path}"
        try:
            # 过滤掉可能导致下游异常的headers
            excluded_headers = {"host", "content-length", "accept-encoding", "connection"}
            headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}
            body = await request.body()
            # 日志可选保留
            print("[dynamic_router] method:", request.method)
            print("[dynamic_router] headers:", headers)
            print("[dynamic_router] body length:", len(body))
            # 保证body为bytes类型
            if isinstance(body, str):
                body = body.encode("utf-8")
            async with httpx.AsyncClient() as client:
                proxy_request = client.build_request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body
                )
                response = await client.send(proxy_request)
                
                # 记录注册服务调用历史
                try:
                    # 尝试解析请求体为JSON
                    request_body = None
                    if body:
                        try:
                            request_body = json.loads(body.decode('utf-8'))
                        except:
                            request_body = body.decode('utf-8', errors='ignore')
                    
                    # 尝试解析响应体为JSON
                    response_body = None
                    if response.content:
                        try:
                            response_body = response.json()
                        except:
                            response_body = response.content.decode('utf-8', errors='ignore')
                    
                    history_records.append({
                        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                        "api": f"/{path}",
                        "service_name": service_info.get("name", path),
                        "service_type": "registered_service",
                        "method": request.method,
                        "params": {
                            "headers": dict(headers),
                            "body": request_body
                        },
                        "result": {
                            "status_code": response.status_code,
                            "content": response_body
                        }
                    })
                    print(f"[dynamic_router] History recorded for {path}")
                except Exception as history_error:
                    print(f"[dynamic_router] History recording error: {history_error}", flush=True)
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers={k: v for k, v in response.headers.items() if k.lower() != "content-encoding"},
                    media_type=response.headers.get("content-type")
                )
        except Exception as e:
            print(f"[dynamic_router] Proxy error: {e}\n{traceback.format_exc()}", flush=True)
            return JSONResponse(content={"error": "Proxy error", "details": str(e)}, status_code=500)
    return JSONResponse(content={"error": "Not found"}, status_code=404)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    print(f"[middleware] 收到请求: {request.method} {request.url.path}", flush=True)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    print(f"[middleware] 响应状态: {response.status_code}", flush=True)
    return response

@app.get("/get_model_health")
async def get_model_health():
    # Normalize status values to English for API consumers
    def normalize_status(v):
        if isinstance(v, str):
            return {"可用": "available", "未知": "unknown", "下线": "offline"}.get(v, v)
        return v
    return JSONResponse(content={
        m["name"]: {"health": normalize_status(m.get("health", "unknown")), "status": normalize_status(m.get("status", "available"))} for m in llm_manager.models
    })

@app.get("/get_model_qps")
async def get_model_qps():
    global llm_manager
    return JSONResponse(content={
        m["name"]: qps_monitor.get_qps(m["name"]) for m in llm_manager.models
    })

@app.get("/get_model_hit_count")
async def get_model_hit_count():
    import core.statistics
    return JSONResponse(content={
        "hit_counter": core.statistics.model_hit_counter,
        "total_request_count": core.statistics.total_request_count
    })

@app.get("/get_model_cost")
async def get_model_cost():
    import core.statistics
    return JSONResponse(content=core.statistics.model_cost_counter)

@app.get("/get_model_cost_user_app")
async def get_model_cost_user_app(user_id: str = None, app_id: str = None):
    import core.statistics
    # 支持聚合查询
    result = {}
    for (model, u, a), cost in core.statistics.model_cost_counter_user_app.items():
        if (user_id is None or u == user_id) and (app_id is None or a == app_id):
            key = (model, u, a)
            result[str(key)] = cost
    return JSONResponse(content=result)

# 启动时初始化健康检查器
@app.on_event("startup")
def start_health_checker():
    global health_checker
    def get_models():
        global llm_manager
        if llm_manager is None:
            return []
        return llm_manager.models
    def update_model_meta(model_name, meta):
        global llm_manager
        if llm_manager is None:
            return
        for m in llm_manager.models:
            if m["name"] == model_name:
                m.update(meta)
    def check_func(model):
        health_url = model.get("health_check")
        try:
            if health_url:
                # 支持相对路径和绝对路径
                if health_url.startswith("http://") or health_url.startswith("https://"):
                    url = health_url
                else:
                    # 拼接base_url
                    base_url = model.get("base_url") or model.get("target_url")
                    if base_url:
                        url = base_url.rstrip("/") + "/" + health_url.lstrip("/")
                    else:
                        url = health_url
                resp = requests.get(url, timeout=300)
                return resp.status_code == 200
            # fallback: 尝试client，客户端已经预先创建，可以验证连接
            if model.get("sync_client") is not None:
                try:
                    # 尝试一个简单的API调用来验证连接
                    client = model["sync_client"]
                    # 这里可以添加一个简单的健康检查调用
                    return True
                except Exception:
                    return False
            # 如果客户端不存在，返回False
            return False
        except Exception:
            return False
    health_checker = HealthChecker(get_models, update_model_meta, check_func)
    health_checker.start(qps_monitor)

@app.get("/plugin/list")
async def plugin_list():
    return [{"name": k, "module": v[1]} for k, v in plugin_registry.items()]

# service-discovery/list接口直接读取service_registry中的status字段
@app.get("/service-discovery/list")
async def service_discovery_list():
    # 每次都从文件加载最新状态，避免多进程/多线程下内存不同步
    def load_service_registry_latest():
        if os.path.exists(SERVICE_REGISTRY_FILE):
            with FileLock(SERVICE_REGISTRY_LOCK):
                with open(SERVICE_REGISTRY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        return {}
    latest_registry = load_service_registry_latest()
    services = []
    for endpoint, info in latest_registry.items():
        services.append({
            "endpoint": endpoint,
            "target_url": info.get("target_url"),
            "health_check": info.get("health_check"),
            "status": info.get("status", "unknown"),
            "desc": info.get("desc", ""),
            "last_update_time": info.get("last_update_time", "")
        })
    # 2. 插件能力发现
    plugins = []
    for func_name, (func, module_name) in plugin_registry.items():
        import inspect
        sig = inspect.signature(func)
        params = [name for name in sig.parameters.keys()]
        plugins.append({
            "name": func_name,
            "module": module_name,
            "params": params,
            "doc": func.__doc__ or ""
        })
    return JSONResponse(content={
        "registered_services": services,
        "plugin_abilities": plugins
    })

async def batch_concurrent(items, handler, max_concurrency=10):
    sem = asyncio.Semaphore(max_concurrency)
    async def sem_handler(item):
        async with sem:
            ctx = contextvars.copy_context()
            async def run_with_ctx():
                if isinstance(item, dict):
                    llm_params = {}
                    for k in ["model_name", "temperature", "tags", "biz_level", "prefer_cost", "session_id", "preferred_index", "top_p", "max_tokens", "stop"]:
                        if k in item:
                            llm_params[k] = item[k]
                    if llm_params:
                        llm_context.set(llm_params)
                if asyncio.iscoroutinefunction(handler):
                    return await handler(**item) if isinstance(item, dict) else await handler(item)
                else:
                    return handler(**item) if isinstance(item, dict) else handler(item)
            if asyncio.iscoroutinefunction(handler):
                return await ctx.run(run_with_ctx)
            else:
                return ctx.run(run_with_ctx)
    return await asyncio.gather(*(sem_handler(item) for item in items))

history_records = []

@app.post("/plugin/invoke")
async def plugin_invoke(
    plugin_name: str,
    model_name: str = Body(None),
    payload: dict = Body(None),
    batch_payload: list = Body(None),
    request: Request = None,
    session_id: str = Cookie(None)
):
    # --- 自动设置 LLM 路由上下文 ---
    llm_params = (payload or {}).copy()
    # 优先从 session 读取 preferred_index
    sid = session_id or (request.cookies.get("session_id") if request else None)
    preferred_index = None
    if sid:
        preferred_index = state_manager.get_preferred_model_index(sid)
        if preferred_index is not None:
                        # 获取模型名
            global llm_manager
            if 0 <= preferred_index < len(llm_manager.models):
                preferred_model_name = llm_manager.models[preferred_index]["name"]
                # 只有未显式指定 model_name 时才注入
                if not model_name:
                    llm_params["model_name"] = preferred_model_name
    if batch_payload and isinstance(batch_payload, list) and len(batch_payload) > 0 and isinstance(batch_payload[0], dict):
        for k in ["model_name", "temperature", "tags", "biz_level", "prefer_cost", "session_id", "preferred_index", "top_p", "max_tokens", "stop"]:
            if k in batch_payload[0]:
                llm_params[k] = batch_payload[0][k]
    llm_context.set(llm_params)
    if not PLUGINS_BATCH_DISPATCH_ENABLED:
        return JSONResponse(content={"error": "插件批量分发功能已关闭"}, status_code=403)
    plugin_func = None
    if plugin_name in plugin_registry:
        plugin_func, _ = plugin_registry[plugin_name]
    else:
        return JSONResponse(content={"error": f"Plugin {plugin_name} not found"}, status_code=404)
    sig = inspect.signature(plugin_func)
    params = sig.parameters
    # 批量处理
    if batch_payload is not None:
        # --- 强制为每个 item 设置 model_name ---
        outer_model_name = model_name
        if outer_model_name:
            batch_payload = [
                {**item, "model_name": outer_model_name} if isinstance(item, dict) else item
                for item in batch_payload
            ]
        # --- END ---
        if any(p in params for p in ["articles", "batch_payload", "docs", "inputs"]):
            batch_param = next(p for p in ["articles", "batch_payload", "docs", "inputs"] if p in params)
            result = plugin_func(**{batch_param: batch_payload})
            history_records.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "api": f"/plugin/invoke?plugin_name={plugin_name}",
                "service_name": plugin_name,
                "service_type": "plugin",
                "method": "POST",
                "params": batch_payload,
                "result": result
            })
            return {"result": result}
        else:
            results = await batch_concurrent(batch_payload, plugin_func, max_concurrency=5)
            history_records.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "api": f"/plugin/invoke?plugin_name={plugin_name}",
                "service_name": plugin_name,
                "service_type": "plugin",
                "method": "POST",
                "params": batch_payload,
                "result": results
            })
            return {"results": results}
    elif payload is not None:
        result = plugin_func(**payload)
        history_records.append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "api": f"/plugin/invoke?plugin_name={plugin_name}",
            "service_name": plugin_name,
            "service_type": "plugin",
            "method": "POST",
            "params": payload,
            "result": result
        })
        return {"result": result}
    else:
        return JSONResponse(content={"error": "参数错误，需提供 payload 或 batch_payload"}, status_code=400)

@app.get("/history")
def get_history():
    return JSONResponse(
        content={"history": history_records},
        headers={"Cache-Control": "no-store"}
    )

@app.on_event("startup")
def init_llm_manager():
    global llm_manager
    if llm_manager is None:
        llm_manager = MultiLLM()
        # 预先创建所有模型的同步客户端，减少首次调用延迟
        print("[init_llm_manager] 开始预先创建所有模型的同步客户端...", flush=True)
        for i, model_info in enumerate(llm_manager.models):
            try:
                # 只创建同步客户端，异步客户端按需创建
                if model_info.get("sync_client") is None:
                    llm_manager._get_sync_client(model_info)
                    print(f"[init_llm_manager] 成功创建同步客户端: {model_info['name']}", flush=True)
                        
            except Exception as e:
                print(f"[init_llm_manager] 创建同步客户端失败: {model_info['name']}, 错误: {e}", flush=True)
        
        print(f"[init_llm_manager] 同步客户端预创建完成，共处理 {len(llm_manager.models)} 个模型", flush=True)

@app.get("/llm_status")
def get_llm_status(model: str = Query(None)):
    # 使用全局llm_manager实例
    global llm_manager
    import core.statistics
    from datetime import datetime, timedelta
    try:
        history = getattr(core.statistics, 'model_call_history', None)
        if history:
            now = datetime.now()
            days = 7
            dates = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days-1, -1, -1)]
            calls = [0 for _ in range(days)]
            for rec in history:
                t = rec.get('time')
                m = rec.get('model')
                if model and m != model:
                    continue
                if isinstance(t, str):
                    t = t[:10]
                else:
                    t = t.strftime('%Y-%m-%d')
                if t in dates:
                    idx = dates.index(t)
                    calls[idx] += 1
            return {"llm_status": llm_manager.llm_status, "dates": dates, "calls": calls}
        else:
            # 没有历史，直接返回累计
            if model:
                total = core.statistics.model_hit_counter.get(model, 0)
            else:
                total = sum(core.statistics.model_hit_counter.values())
            return {"llm_status": llm_manager.llm_status, "dates": ["累计"], "calls": [total]}
    except Exception as e:
        return {"llm_status": llm_manager.llm_status, "dates": [], "calls": []}

def load_llm_models():
    with open(LLM_YAML_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)['models']

def save_llm_models(models):
    with open(LLM_YAML_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump({'models': models}, f, allow_unicode=True)

@app.get('/api/llm/list')
def list_llm():
    return {'models': load_llm_models()}

@app.post('/api/llm/add')
def add_llm(model: dict = Body(...)):
    meta = model.get('meta', {})
    tags = meta.get('tags', model.get('tags', []))
    status = meta.get('status', model.get('status', '可用'))
    qps = meta.get('qps', model.get('qps', 0))
    cost = meta.get('cost', model.get('cost', 0.0))
    # 兼容前端传来的高级元数据字段
    max_input_length = model.get('max_input_length', meta.get('max_input_length', 2048))
    supported_tasks = model.get('supported_tasks', meta.get('supported_tasks', []))
    languages = model.get('languages', meta.get('languages', []))
    effect_score = model.get('effect_score', meta.get('effect_score', 5.0))
    description = model.get('description', meta.get('description', ''))
    # 写入meta分组
    model['meta'] = {
        'tags': tags,
        'status': status,
        'qps': qps,
        'cost': cost,
        'max_input_length': max_input_length,
        'supported_tasks': supported_tasks,
        'languages': languages,
        'effect_score': effect_score,
        'description': description,
    }
    # 同步顶层字段，兼容老逻辑
    model['tags'] = tags
    model['status'] = status
    model['qps'] = qps
    model['cost'] = cost
    models = load_llm_models()
    if any(m['name'] == model['name'] for m in models):
        return JSONResponse(content={'error': '模型已存在'}, status_code=400)
    models.append(model)
    save_llm_models(models)
    # 热重载
    if hasattr(globals(), 'llm_manager') and llm_manager:
        llm_manager.__init__()
    return {'success': True}

@app.post('/api/llm/update')
def update_llm(model: dict = Body(...)):
    models = load_llm_models()
    for i, m in enumerate(models):
        if m['name'] == model['name']:
            # 兼容前端传来的高级元数据字段
            meta = m.get('meta', {})
            meta['max_input_length'] = model.get('max_input_length', meta.get('max_input_length', 2048))
            meta['supported_tasks'] = model.get('supported_tasks', meta.get('supported_tasks', []))
            meta['languages'] = model.get('languages', meta.get('languages', []))
            meta['effect_score'] = model.get('effect_score', meta.get('effect_score', 5.0))
            meta['description'] = model.get('description', meta.get('description', ''))
            # 兼容基础字段
            meta['tags'] = model.get('tags', meta.get('tags', []))
            meta['status'] = model.get('status', meta.get('status', '可用'))
            meta['qps'] = model.get('qps', meta.get('qps', 0))
            meta['cost'] = model.get('cost', meta.get('cost', 0.0))
            m['meta'] = meta
            m['tags'] = meta['tags']
            m['status'] = meta['status']
            m['qps'] = meta['qps']
            m['cost'] = meta['cost']
            m['version'] = model.get('version', m.get('version', ''))
            m['url'] = model.get('url', m.get('url', ''))
            m['key'] = model.get('key', m.get('key', ''))
            save_llm_models(models)
            if hasattr(globals(), 'llm_manager') and llm_manager:
                llm_manager.__init__()
            return {'success': True}
    return JSONResponse(content={'error': '模型不存在'}, status_code=404)

@app.post('/api/llm/delete')
def delete_llm(model: dict = Body(...)):
    models = load_llm_models()
    models = [m for m in models if m['name'] != model['name']]
    save_llm_models(models)
    if hasattr(globals(), 'llm_manager') and llm_manager:
        llm_manager.__init__()
    return {'success': True}

@app.get("/api/readme/sections")
def get_readme_sections(lang: Optional[str] = None):
    readme_file = os.path.join(BASE_DIR, "README.md")
    if lang and str(lang).lower().startswith("zh"):
        zh_file = os.path.join(BASE_DIR, "README_zh-CN.md")
        if os.path.exists(zh_file):
            readme_file = zh_file
    with open(readme_file, encoding="utf-8") as f:
        content = f.read()
    # 匹配所有一级标题（# ）
    sections = re.findall(r"^# +(.+)$", content, re.MULTILINE)
    # 生成锚点
    anchors = [re.sub(r'[^\w\u4e00-\u9fa5]+', '-', s.strip()).strip('-').lower() for s in sections]
    return JSONResponse(content={"sections": [{"title": t, "anchor": a} for t, a in zip(sections, anchors)]})

@app.get("/api/readme/section")
def get_readme_section(title: str, lang: Optional[str] = None):
    readme_file = os.path.join(BASE_DIR, "README.md")
    if lang and str(lang).lower().startswith("zh"):
        zh_file = os.path.join(BASE_DIR, "README_zh-CN.md")
        if os.path.exists(zh_file):
            readme_file = zh_file
    with open(readme_file, encoding="utf-8") as f:
        content = f.read()
    # 找到指定一级标题及其下所有内容，直到下一个一级标题
    pattern = rf"(^# +{re.escape(title)}\s*$)([\s\S]*?)(?=^# +|\Z)"
    m = re.search(pattern, content, re.MULTILINE)
    if not m:
        return JSONResponse(content={"error": "Section not found"}, status_code=404)
    section_md = m.group(1) + m.group(2)
    return JSONResponse(content={"markdown": section_md}) 