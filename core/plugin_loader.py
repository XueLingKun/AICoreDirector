from core.state_manager import state_manager 

import importlib
import os
import pkgutil
import inspect
from fastapi import Body
from fastapi import Request
from pydantic import create_model
import uuid
import time
from core.logging_config import logger

plugin_registry = {}

# 装饰器：注册插件API
def plugin_api(func):
    plugin_registry[func.__name__] = (func, func.__module__)
    return func

# 获取插件API的FastAPI路由适配器
def get_plugin_func(func, module_name, func_name):
    sig = inspect.signature(func)
    param_names = list(sig.parameters.keys())
    # 动态生成Pydantic模型用于POST JSON body，兼容Pydantic v2
    if param_names:
        fields = {}
        for name, param in sig.parameters.items():
            annotation = param.annotation if param.annotation != inspect._empty else str
            default = param.default if param.default != inspect._empty else ...
            fields[name] = (annotation, default)
        Model = create_model(f"{func_name}_Body", **fields)
        async def endpoint(body: Model = Body(...)):
            request_id = str(uuid.uuid4())
            start = time.time()
            try:
                kwargs = body.dict()
                result = func(**kwargs)
                logger.info({
                    "event": "plugin_api_call",
                    "plugin": func_name,
                    "module": module_name,
                    "request_id": request_id,
                    "success": True,
                    "duration_ms": int((time.time() - start) * 1000),
                    "params": kwargs,
                })
                return result
            except Exception as e:
                logger.error({
                    "event": "plugin_api_call",
                    "plugin": func_name,
                    "module": module_name,
                    "request_id": request_id,
                    "success": False,
                    "duration_ms": int((time.time() - start) * 1000),
                    "params": kwargs,
                    "error": str(e),
                })
                raise
        endpoint.__name__ = func_name
        return endpoint
    else:
        async def endpoint():
            return func()
        endpoint.__name__ = func_name
        return endpoint

# 扫描 business 目录下所有插件并注册
def scan_and_register_plugins(app=None):
    import business
    for _, modname, _ in pkgutil.iter_modules(business.__path__):
        importlib.import_module(f'business.{modname}')
    if app is not None:
        for func_name, (func, module_name) in plugin_registry.items():
            route_path = f"/{func_name}"
            if route_path not in [route.path for route in app.routes]:
                print(f"[PluginLoader] 注册插件API路由: {route_path}")
                app.add_api_route(route_path, get_plugin_func(func, module_name, func_name), methods=["GET", "POST"])

# 插件热加载扫描间隔（秒）
def get_plugin_scan_interval():
    return 2 