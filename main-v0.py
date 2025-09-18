from fastapi import FastAPI, Request, Response, Cookie, Query, Body
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
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
from core.statistics import model_hit_counter, model_cost_counter, model_cost_counter_user_app
from api import prompt_api
import yaml
import re
import requests
import contextvars

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prompt_api.router, prefix="/api")
app.include_router(prompt_api.router)

SESSION_COOKIE_NAME = "session_id"

# 全局监控器实例
qps_monitor = QPSMonitor()
health_checker = None  # 启动时初始化

router = ModelRouter(lambda: llm.models)

SERVICE_REGISTRY_FILE = "service_registry.json"
SERVICE_REGISTRY_LOCK = "service_registry.json.lock"

# 插件批量并发调度开关
PLUGINS_BATCH_DISPATCH_ENABLED = True  # 设为False可一键禁用该逻辑

# 全局 LLM 实例（假设只初始化一次）
llm_manager: MultiLLM = None

LLM_YAML_PATH = 'llm_models.yaml'

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

@app.post("/set_preferred_model")
async def set_preferred_model(request: Request, response: Response, preferred_model_info: SetPreferredModelRequest, session_id: str = Cookie(None)):
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(key=SESSION_COOKIE_NAME, value=session_id)
    model_name_to_find = preferred_model_info.model_name
    preferred_index = -1
    for i, model in enumerate(llm.models):
        if model["name"] == model_name_to_find:
            preferred_index = i
            break
    if preferred_index != -1:
        state_manager.set_preferred_model_index(session_id, preferred_index)
        try:
            model_info = llm.models[preferred_index]
            llm._get_sync_client(model_info)
            await llm._get_async_client(model_info)
        except Exception as e:
            print(f"[api:/set_preferred_model] Could not create client: {e}", flush=True)
        return JSONResponse(content={
            "message": f"Preferred model set to {model_name_to_find} for session {session_id}.",
            "preferred_model_index": preferred_index,
            "session_id": session_id
        })
    else:
        return JSONResponse(content={
            "message": f"Model {model_name_to_find} not found in configured models.",
            "available_models": [m["name"] for m in llm.models],
            "session_id": session_id
        }, status_code=404)

def llm_stream_generator(prompt, model_name, temperature=None, top_p=None, max_tokens=None, stop=None):
    # 如果llm有原生流式方法，优先用
    if hasattr(llm, 'generate_stream_with_specific_model'):
        yield from llm.generate_stream_with_specific_model(
            prompt=prompt,
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop
        )
    else:
        # 兼容：一次性返回全部内容
        result_obj = llm.generate_with_specific_model(
            prompt=prompt,
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop
        )
        yield result_obj.get("result")

@app.post("/llm_invoke")
async def LLM_invoke(request: LLMInvokeRequest, stream: bool = Query(False)):
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
        if model_name:
            idx = next((i for i, m in enumerate(llm.models) if m["name"] == model_name), None)
            if idx is not None:
                model = llm.models[idx]
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
        # 成本统计
        global model_cost_counter
        model_cost_counter[model_name] = model_cost_counter.get(model_name, 0.0)
        # 用户/应用维度成本统计
        global model_cost_counter_user_app
        key = (model_name, user_id or "", app_id or "")
        model_cost_counter_user_app[key] = model_cost_counter_user_app.get(key, 0.0)
        if stream:
            def stream_gen():
                yield from llm_stream_generator(
                    prompt=prompt,
                    model_name=model_name,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    stop=stop
                )
            return StreamingResponse(stream_gen(), media_type="text/plain")
        # 非流式同步返回
        result_obj = llm.generate_with_specific_model(
            prompt=prompt,
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop
        )
        used_model = model_name
        model_cost_counter[model_name] += (result_obj.get("cost") or 0.0)
        key = (model_name, user_id or "", app_id or "")
        model_cost_counter_user_app[key] += (result_obj.get("cost") or 0.0)
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
                "available_models": [m["name"] for m in llm.models],
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
    if action == 'add':
        if not llm.add_LLM(model_name, base_url, api_key, tags, version, status, cost, qps, health):
            return JSONResponse(status_code=409, content={"error": f"Model '{model_name}' already exists in memory."})
        idx = 0
        while os.environ.get(f"MODEL_NAME_{idx}"):
            idx += 1
        set_key(dotenv_path, f"MODEL_NAME_{idx}", model_name)
        set_key(dotenv_path, f"BASE_URL_{idx}", base_url)
        set_key(dotenv_path, f"API_KEY_{idx}", api_key)
        set_key(dotenv_path, f"TAGS_{idx}", ",".join(tags) if tags else "")
        set_key(dotenv_path, f"VERSION_{idx}", version or "")
        set_key(dotenv_path, f"STATUS_{idx}", status or "可用")
        set_key(dotenv_path, f"COST_{idx}", str(cost) if cost is not None else "0.0")
        set_key(dotenv_path, f"QPS_{idx}", str(qps) if qps is not None else "0")
        set_key(dotenv_path, f"HEALTH_{idx}", health or "unknown")
        return {"status": "success", "message": f"Model '{model_name}' added and persisted at index {idx}."}
    elif action == 'update':
        if not llm.update_LLM(model_name, base_url, api_key):
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
        if not llm.remove_LLM(model_name):
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
    result = []
    for model in llm.models:
        meta = model.get('meta', {})
        result.append({
            "name": model["name"],
            "url": model["url"],
            "version": model.get("version", ""),
            "tags": meta.get("tags", []),
            "status": meta.get("status", "可用"),
            "qps": meta.get("qps", 0),
            "cost": meta.get("cost", 0.0),
            "index": llm.models.index(model),
            "health": model.get("health", "unknown"),
            "current_global_model_index": llm.current,
            "current_global_model_name": llm.models[llm.current]["name"] if llm.models else None
        })
    return {"models": result}

@app.get("/get-openapi-schema")
async def get_openapi_schema():
    return JSONResponse(content=app.openapi())

@app.post("/service-registry/register")
async def register_service(service_data: dict):
    service_registry[service_data["endpoint"]] = {
        "target_url": service_data["target_url"],
        "health_check": service_data.get("health_check", ""),
        "desc": service_data.get("desc", "")
    }
    save_service_registry(service_registry)
    return {"status": "success", "registered_endpoint": service_data["endpoint"]}

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

@app.on_event("startup")
def on_startup():
    scan_and_register_plugins(app)
    move_dynamic_router_to_end(app)
    start_plugin_hot_reload(app)
    start_health_checker()
    init_llm_manager()

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
    if path in service_registry:
        service_info = service_registry[path]
        target_url = service_info["target_url"].rstrip("/")
        # 拼接 target_url + "/" + path
        url = f"{target_url}/{path}"
        async with httpx.AsyncClient() as client:
            proxy_request = client.build_request(
                method=request.method,
                url=url,
                headers=dict(request.headers),
                content=await request.body()
            )
            response = await client.send(proxy_request)
            # 将 httpx.Response 转换为 Starlette Response，避免返回 httpx.Response 对象
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() != "content-encoding"},
                media_type=response.headers.get("content-type")
            )
    return JSONResponse(content={"error": "Not found"}, status_code=404)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response

@app.get("/get_model_health")
async def get_model_health():
    return JSONResponse(content={
        m["name"]: {"health": m.get("health", "unknown"), "status": m.get("status", "可用")} for m in llm.models
    })

@app.get("/get_model_qps")
async def get_model_qps():
    return JSONResponse(content={
        m["name"]: qps_monitor.get_qps(m["name"]) for m in llm.models
    })

@app.get("/get_model_hit_count")
async def get_model_hit_count():
    import core.statistics
    return JSONResponse(content={
        "hit_counter": model_hit_counter,
        "total_request_count": core.statistics.total_request_count
    })

@app.get("/get_model_cost")
async def get_model_cost():
    return JSONResponse(content=model_cost_counter)

@app.get("/get_model_cost_user_app")
async def get_model_cost_user_app(user_id: str = None, app_id: str = None):
    # 支持聚合查询
    result = {}
    for (model, u, a), cost in model_cost_counter_user_app.items():
        if (user_id is None or u == user_id) and (app_id is None or a == app_id):
            key = (model, u, a)
            result[str(key)] = cost
    return JSONResponse(content=result)

# 启动时初始化健康检查器
@app.on_event("startup")
def start_health_checker():
    global health_checker
    def get_models():
        return llm.models
    def update_model_meta(model_name, meta):
        for m in llm.models:
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
            # fallback: 尝试client
            client, _ = llm._get_sync_client(model)
            return True
        except Exception:
            return False
    health_checker = HealthChecker(get_models, update_model_meta, check_func)
    health_checker.start(qps_monitor)

@app.get("/plugin/list")
async def plugin_list():
    return [{"name": k, "module": v[1]} for k, v in plugin_registry.items()]

@app.get("/service-discovery/list")
async def service_discovery_list():
    import requests
    services = []
    for endpoint, info in service_registry.items():
        health_check = info.get("health_check")
        status = "未知"
        if health_check:
            try:
                # 支持绝对和相对路径
                if health_check.startswith("http://") or health_check.startswith("https://"):
                    url = health_check
                else:
                    base_url = info.get("target_url")
                    if base_url:
                        url = base_url.rstrip("/") + "/" + health_check.lstrip("/")
                    else:
                        url = health_check
                resp = requests.get(url, timeout=300)
                status = "可用" if resp.status_code == 200 else "下线"
            except Exception:
                status = "下线"
        services.append({
            "endpoint": endpoint,
            "target_url": info.get("target_url"),
            "health_check": health_check,
            "status": status,
            "desc": info.get("desc", "")
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
            if asyncio.iscoroutinefunction(handler):
                return await handler(**item) if isinstance(item, dict) else await handler(item)
            else:
                raise RuntimeError("handler 必须为 async 协程函数以支持 contextvars 全链路自动获取")
    tasks = [sem_handler(item) for item in items]
    return await asyncio.gather(*tasks)

history_records = []

@app.post("/plugin/invoke")
async def plugin_invoke(
    plugin_name: str,
    payload: dict = Body(None),
    batch_payload: list = Body(None)
):
    # --- 自动设置 LLM 路由上下文 ---
    llm_params = (payload or {}).copy()
    if batch_payload and isinstance(batch_payload, list) and len(batch_payload) > 0 and isinstance(batch_payload[0], dict):
        # 优先用 batch_payload[0] 的参数（如 model_name），否则用 payload
        for k in ["model_name", "temperature", "tags", "biz_level", "prefer_cost", "session_id", "preferred_index", "top_p", "max_tokens", "stop"]:
            if k in batch_payload[0]:
                llm_params[k] = batch_payload[0][k]
    llm_context.set(llm_params)
    if not PLUGINS_BATCH_DISPATCH_ENABLED:
        return JSONResponse(content={"error": "插件批量分发功能已关闭"}, status_code=403)
    plugin_func = None
    # 动态查找插件
    if plugin_name in plugin_registry:
        plugin_func, _ = plugin_registry[plugin_name]
    else:
        return JSONResponse(content={"error": f"Plugin {plugin_name} not found"}, status_code=404)
    sig = inspect.signature(plugin_func)
    params = sig.parameters
    # 批量处理
    if batch_payload is not None:
        # --- 修正：批量时自动补充 model_name ---
        outer_model_name = None
        if payload and "model_name" in payload:
            outer_model_name = payload["model_name"]
        if outer_model_name:
            for item in batch_payload:
                if isinstance(item, dict) and "model_name" not in item:
                    item["model_name"] = outer_model_name
        # --- END ---
        if any(p in params for p in ["articles", "batch_payload", "docs", "inputs"]):
            batch_param = next(p for p in ["articles", "batch_payload", "docs", "inputs"] if p in params)
            result = plugin_func(**{batch_param: batch_payload})
            # 记录历史
            history_records.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "api": f"/plugin/invoke?plugin_name={plugin_name}",
                "params": batch_payload,
                "result": result
            })
            return {"result": result}
        else:
            results = await batch_concurrent(batch_payload, plugin_func, max_concurrency=5)
            # 记录历史
            history_records.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "api": f"/plugin/invoke?plugin_name={plugin_name}",
                "params": batch_payload,
                "result": results
            })
            return {"results": results}
    elif payload is not None:
        result = plugin_func(**payload)
        # 记录历史
        history_records.append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "api": f"/plugin/invoke?plugin_name={plugin_name}",
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

@app.get("/llm_status")
def get_llm_status(model: str = Query(None)):
    global llm_manager
    if llm_manager is None:
        return {"error": "LLM manager not initialized"}
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
    # 写入meta分组
    model['meta'] = {
        'tags': tags,
        'status': status,
        'qps': qps,
        'cost': cost,
        # ... 其他meta字段 ...
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
            models[i].update(model)
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
def get_readme_sections():
    with open("README.md", encoding="utf-8") as f:
        content = f.read()
    # 匹配所有一级标题（# ）
    sections = re.findall(r"^# +(.+)$", content, re.MULTILINE)
    # 生成锚点
    anchors = [re.sub(r'[^\w\u4e00-\u9fa5]+', '-', s.strip()).strip('-').lower() for s in sections]
    return JSONResponse(content={"sections": [{"title": t, "anchor": a} for t, a in zip(sections, anchors)]})

@app.get("/api/readme/section")
def get_readme_section(title: str):
    with open("README.md", encoding="utf-8") as f:
        content = f.read()
    # 找到指定一级标题及其下所有内容，直到下一个一级标题
    pattern = rf"(^# +{re.escape(title)}\s*$)([\s\S]*?)(?=^# +|\Z)"
    m = re.search(pattern, content, re.MULTILINE)
    if not m:
        return JSONResponse(content={"error": "Section not found"}, status_code=404)
    section_md = m.group(1) + m.group(2)
    return JSONResponse(content={"markdown": section_md}) 