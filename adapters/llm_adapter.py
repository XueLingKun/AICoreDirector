"""
批量插件调用的模型路由方案

本项目支持在批量/并发插件调用时，通过 contextvars（上下文变量）自动感知和传递如 model_name、temperature、tags 等 LLM 路由参数。

- 调用端：只需在请求体中指定一次 model_name，后端会自动为每个批量 item 补充。
- 后端链路：API 层通过 contextvars.set 自动注入，所有业务/插件/LLM 层无需层层传递参数。
- LLM 层：自动从 contextvars 获取当前数，确保每条请求严格走指定模型。

优势：
- 无需每层函数都加 model_name 参数，代码更简洁、易维护。
- 支持高并发、批量任务下的参数隔离和自动感知。
- 只需在入口和 LLM 层处理，业务逻辑零侵入。

示例：
    resp = requests.post(
        f"http://127.0.0.1:8000/plugin/invoke?plugin_name=extract_",
        json={
            "batch_payload": batch_payload,
            "model_name": "GLM-4-Flash"
        }
    )
所有批量请求都将严格走你指定的模型，无需层层传递。
"""
import os
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI, OpenAIError
import asyncio
import typing
from core.logging_config import logger
import uuid
import time
import core.statistics
from core.statistics import model_hit_counter, model_cost_counter
import yaml
import contextvars

load_dotenv()

ENABLE_SMART_ROUTING = True  # 智能分流开关，关闭则始终用当前模型

llm_context: contextvars.ContextVar = contextvars.ContextVar('llm_context', default={})

class MultiLLM:
    def __init__(self):
        print("[MultiLLM.__init__] Starting initialization...", flush=True)
        # 从 YAML 加载模型配置
        with open('llm_models.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        all_configs = config['models']
        self.models = []
        DEFAULT_META = {
            "qps": 2,
            "cost": 0.0,
            "latency": 1000,
            "error_rate": 0.0,
            "max_input_length": 2048,
            "effect_score": 5.0,
            "health": "unknown",
            "supported_tasks": [],
            "languages": [],
            "description": "",
            "vendor": "",
            "tags": [],
        }
        for m in all_configs:
            meta = m.get('meta', {})
            # 合并默认值
            meta = {**DEFAULT_META, **meta}
            m['meta'] = meta
            # 兼容老字段，优先meta
            m['tags'] = meta.get('tags', m.get('tags', []))
            m['status'] = meta.get('status', m.get('status', '可用'))
            m['qps'] = meta.get('qps', m.get('qps', 2))
            m['cost'] = meta.get('cost', m.get('cost', 0.0))
            m['version'] = m.get('version', '')
            m['sync_client'] = None
            m['async_client'] = None
            self.models.append(m)
        self.current = 0
        print(f"[MultiLLM.__init__] Initialization complete. Total usable model configs stored: {len(self.models)}", flush=True)

        self.llm_status = {}
        for m in self.models:
            self.llm_status[m['name']] = {
                'current_concurrency': 0,
                'max_concurrency': m.get('qps', 2) or 2,  # 默认2，便于测试分流
                'healthy': m.get('status', '可用') == '可用',
                'latency': 0.0,      # ms，滑动平均
                'error_rate': 0.0,   # 近N次错误率
                'cost': m.get('cost', 0.0) or 0.0,  # 单位成本
                'call_count': 0,
                'error_count': 0
            }
        self.latency_alpha = 0.3  # 滑动平均系数
        self.error_window = 20    # 错误率统计窗口
        self._error_history = {m['name']: [] for m in self.models}

    def _next(self):
        # 切换到下一个模型，如果到达末尾则回到第一个
        self.current = (self.current + 1) % len(self.models)
        print(f"Switched to next model candidate: {self.models[self.current]['name']} (Index: {self.current} in usable list)", flush=True)

    def _create_sync_client(self, model_config: dict) -> OpenAI:
        """Creates and returns a synchronous OpenAI client for the given configuration."""
        url = model_config["url"]
        key = model_config["key"]
        name = model_config["name"]
        # print(f"[MultiLLM._create_sync_client] Attempting to create sync client for model: {name}", flush=True)
        client = OpenAI(base_url=url, api_key=key)
        # print(f"[MultiLLM._create_sync_client] Sync client created successfully for model: {name}", flush=True)
        return client

    def _get_sync_client(self, model_info: dict | None = None) -> tuple[OpenAI, str]:
        """Gets or creates the synchronous client for the given model info. If model_info is None, uses the current model."""
        if model_info is None:
            # Use the current model if no model_info is provided
            model_info = self.models[self.current]

        model_name = model_info["name"]
        # print(f"[MultiLLM._get_sync_client] Getting sync client for model: {model_name} (Index: {self.models.index(model_info)} in usable list)", flush=True)

        if model_info["sync_client"] is None:
            try:
                # Pass model_info to create method
                model_info["sync_client"] = self._create_sync_client(model_info)
                print(f"[MultiLLM._get_sync_client] Sync client created successfully for model: {model_name}", flush=True)
            except Exception as e:
                 # If client creation failed, raise the error (switching is handled in generate)
                print(f"[MultiLLM._get_sync_client] Failed to create sync client for {model_name}: {e}", flush=True)
                raise e

        # Return the client and the model name
        return model_info["sync_client"], model_name

    def _create_async_client(self, model_config) -> AsyncOpenAI:
         """Creates and returns an asynchronous OpenAI client for the given configuration."""
         url = model_config["url"]
         key = model_config["key"]
         name = model_config["name"]
         # print(f"[MultiLLM._create_async_client] Attempting to create async client for model: {name}", flush=True)
         client = AsyncOpenAI(base_url=url, api_key=key)
         # print(f"[MultiLLM._create_async_client] Async client created successfully for model: {name}", flush=True)
         return client

    async def _get_async_client(self, model_info: dict | None = None) -> tuple[AsyncOpenAI, str]:
         """Gets or creates the asynchronous client for the given model info. If model_info is None, uses the current model."""
         if model_info is None:
             # Use the current model if no model_info is provided
             model_info = self.models[self.current]

         model_name = model_info["name"]
         # print(f"[MultiLLM._get_async_client] Getting async client for model: {model_name} (Index: {self.models.index(model_info)} in usable list)", flush=True)

         if model_info["async_client"] is None:
            try:
                 # No await here, _create_async_client is not async
                 model_info["async_client"] = self._create_async_client(model_info)
                 print(f"[MultiLLM._get_async_client] Async client created successfully for model: {model_name}", flush=True)
            except Exception as e:
                 # If client creation failed, raise the error (switching is handled in async_generate)
                print(f"[MultiLLM._get_async_client] Failed to create async client for {model_name}: {e}", flush=True)
                raise e

         # Return the client and the model name
         return model_info["async_client"], model_name

    def _select_llm_candidates(self, model_name=None, biz_level=None, prefer_cost=None, tags=None):
        # 1. model_name 强制指定
        if model_name:
            return [m for m in self.models if m['name'] == model_name]

        # 2. 先筛健康、可用、并发未超限
        candidates = [m for m in self.models if self.llm_status[m['name']]['healthy'] and self.llm_status[m['name']]['current_concurrency'] < self.llm_status[m['name']]['max_concurrency']]
        if not candidates:
            candidates = [m for m in self.models if self.llm_status[m['name']]['healthy']]
        if not candidates:
            candidates = self.models  # 全部超载或不健康时兜底

        # 3. biz_level 过滤
        if biz_level:
            if biz_level == "premium":
                candidates = [m for m in candidates if m.get("cost", 0) >= 0.05]
            elif biz_level == "economy":
                candidates = [m for m in candidates if m.get("cost", 0) <= 0.02]
            # 你可以根据实际模型配置调整阈值

        # 4. prefer_cost 过滤/排序
        if prefer_cost == "low":
            if candidates:
                min_cost = min(m.get("cost", 0) for m in candidates)
                candidates = [m for m in candidates if m.get("cost", 0) == min_cost]
        elif prefer_cost == "high":
            if candidates:
                max_cost = max(m.get("cost", 0) for m in candidates)
                candidates = [m for m in candidates if m.get("cost", 0) == max_cost]

        # 5. tags 过滤
        if tags:
            candidates = [m for m in candidates if set(tags).issubset(set(m.get("tags", [])))]

        # 6. 综合排序
        def score(m):
            s = self.llm_status[m['name']]
            return (
                s['error_rate'] * 1000 +
                s['latency'] * 0.1 +
                s['cost'] * 10 +
                s['current_concurrency'] * 5
            )
        return sorted(candidates, key=score)

    def generate(self, prompt, model_name=None, temperature=None, top_p=None, max_tokens=None, stop=None, **kwargs):
        # 优先从 contextvars 获取 LLM 路由参数
        ctx = llm_context.get({})
        model_name = model_name or ctx.get('model_name')
        temperature = temperature if temperature is not None else ctx.get('temperature')
        top_p = top_p if top_p is not None else ctx.get('top_p')
        max_tokens = max_tokens if max_tokens is not None else ctx.get('max_tokens')
        stop = stop if stop is not None else ctx.get('stop')
        # 如果指定了 model_name，则强制只用该模型
        if model_name:
            return self.generate_with_specific_model(
                prompt=prompt,
                model_name=model_name,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stop=stop,
                **kwargs
            )
        # 否则走原有分流逻辑
        core.statistics.total_request_count += 1
        request_id = str(uuid.uuid4())
        start = time.time()
        candidates = self._select_llm_candidates()
        last_exception = None
        for model_info in candidates:
            model_name_for_log = model_info['name']
            print(f"[MultiLLM.generate] Using model: {model_name_for_log} (智能分流={ENABLE_SMART_ROUTING})", flush=True)
            self.llm_status[model_name_for_log]['current_concurrency'] += 1
            self.llm_status[model_name_for_log]['call_count'] += 1
            try:
                client, used_model_name = self._get_sync_client(model_info)
                messages = []
                if temperature is not None or top_p is not None or max_tokens is not None or stop is not None:
                    messages.append({"role": "system", "content": f"You are a helpful assistant, your temperature is {temperature}, top_p is {top_p}, max_tokens is {max_tokens}, and stop is {stop}."})
                messages.append({"role": "user", "content": prompt})
                print(f"[MultiLLM.generate] Calling client.chat.completions.create with model '{used_model_name}'...", flush=True)
                t0 = time.time()
                response = client.chat.completions.create(
                    model=used_model_name,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    stop=stop,
                )
                latency = (time.time() - t0) * 1000  # ms
                s = self.llm_status[model_name_for_log]
                s['latency'] = latency if s['latency'] == 0 else (self.latency_alpha * latency + (1 - self.latency_alpha) * s['latency'])
                self._error_history[model_name_for_log].append(0)
                if len(self._error_history[model_name_for_log]) > self.error_window:
                    self._error_history[model_name_for_log].pop(0)
                s['error_rate'] = sum(self._error_history[model_name_for_log]) / len(self._error_history[model_name_for_log])
                content = response.choices[0].message.content
                token_usage = getattr(response, 'usage', None)
                total_tokens = token_usage.total_tokens if token_usage and hasattr(token_usage, 'total_tokens') else None
                model_info2 = next((m for m in self.models if m['name'] == used_model_name), None)
                cost_per_token = model_info2.get('cost', 0.0) if model_info2 else 0.0
                cost = (total_tokens or 0) * cost_per_token if cost_per_token else None
                from core.statistics import record_model_cost, record_model_call
                record_model_cost(model_name_for_log, cost or 0.0)
                record_model_call(model_name_for_log)
                logger.info({
                    "event": "llm_generate",
                    "model": used_model_name,
                    "meta": model_info2.get("meta", {}) if model_info2 else {},
                    "request_id": request_id,
                    "success": True,
                    "duration_ms": int((time.time() - start) * 1000),
                    "prompt_len": len(prompt),
                    "token_usage": total_tokens,
                    "cost": cost,
                    "params": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "max_tokens": max_tokens,
                        "stop": stop
                    },
                    # "user_id": user_id,  # 如有可补充
                })
                return {
                    "result": content,
                    "used_model": used_model_name,
                    "token_usage": total_tokens,
                    "cost": cost
                }
            except Exception as e:
                last_exception = e
                s = self.llm_status[model_name_for_log]
                self._error_history[model_name_for_log].append(1)
                if len(self._error_history[model_name_for_log]) > self.error_window:
                    self._error_history[model_name_for_log].pop(0)
                s['error_rate'] = sum(self._error_history[model_name_for_log]) / len(self._error_history[model_name_for_log])
                s['error_count'] += 1
                logger.error({
                    "event": "llm_generate",
                    "model": model_name_for_log,
                    "meta": model_info.get("meta", {}),
                    "request_id": request_id,
                    "success": False,
                    "duration_ms": int((time.time() - start) * 1000),
                    "prompt_len": len(prompt),
                    "error": str(e),
                    "params": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "max_tokens": max_tokens,
                        "stop": stop
                    },
                    # "user_id": user_id,  # 如有可补充
                })
            finally:
                self.llm_status[model_name_for_log]['current_concurrency'] -= 1
        # 如果所有候选 LLM 都失败，抛出最后一个异常
        if last_exception:
            raise last_exception

    def add_LLM(self, name, url, key, tags=None, version=None, status=None, cost=None, qps=None, health=None):
        for model in self.models:
            if model["name"] == name:
                return False
        new_model = {
            "url": url,
            "name": name,
            "key": key,
            "version": version or "",
            "meta": {
                "tags": tags or [],
                "status": status or "可用",
                "cost": cost if cost is not None else 0.0,
                "qps": qps if qps is not None else 0,
            },
            "sync_client": None,
            "async_client": None,
            "health": health or "unknown"
        }
        # 同步顶层字段，兼容老逻辑
        new_model["tags"] = new_model["meta"]["tags"]
        new_model["status"] = new_model["meta"]["status"]
        new_model["cost"] = new_model["meta"]["cost"]
        new_model["qps"] = new_model["meta"]["qps"]
        self.models.append(new_model)
        return True

    def update_LLM(self, name, url=None, key=None, tags=None, version=None, status=None, cost=None, qps=None, health=None):
        for model in self.models:
            if model["name"] == name:
                if url is not None:
                    model["url"] = url
                if key is not None:
                    model["key"] = key
                if version is not None:
                    model["version"] = version
                if "meta" not in model:
                    model["meta"] = {}
                if tags is not None:
                    model["meta"]["tags"] = tags
                    model["tags"] = tags
                if status is not None:
                    model["meta"]["status"] = status
                    model["status"] = status
                if cost is not None:
                    model["meta"]["cost"] = cost
                    model["cost"] = cost
                if qps is not None:
                    model["meta"]["qps"] = qps
                    model["qps"] = qps
                if health is not None:
                    model["health"] = health
                model["sync_client"] = None
                model["async_client"] = None
                return True
        return False

    def remove_LLM(self, name):
        for i, model in enumerate(self.models):
            if model["name"] == name:
                del self.models[i]
                # 修正 current 指针
                if hasattr(self, "current") and self.current >= len(self.models):
                    self.current = max(0, len(self.models) - 1)
                return True
        return False

    def generate_with_specific_model(self, prompt, model_name=None, temperature=None, top_p=None, max_tokens=None, stop=None, session_id=None, preferred_index=None, biz_level=None, prefer_cost=None, tags=None, **kwargs):
        print(f"[generate_with_specific_model] 开始处理: model_name='{model_name}', prompt='{prompt[:50]}...'")
        """
        统一入口，自动参数映射，支持 temperature、top_p、max_tokens、stop。
        路由优先级：
        1. model_name 明确指定，强制用该模型。
        2. preferred_index（如 session 绑定）有效，优先用该模型。
        3. 否则按 biz_level/prefer_cost/tags 动态分流。
        """
        # 优先级1：model_name 显式参数 > 上下文参数
        ctx = llm_context.get({})
        model_name = model_name or ctx.get('model_name')
        temperature = temperature if temperature is not None else ctx.get('temperature')
        top_p = top_p if top_p is not None else ctx.get('top_p')
        max_tokens = max_tokens if max_tokens is not None else ctx.get('max_tokens')
        stop = stop if stop is not None else ctx.get('stop')
        session_id = session_id or ctx.get('session_id')
        preferred_index = preferred_index if preferred_index is not None else ctx.get('preferred_index')
        biz_level = biz_level or ctx.get('biz_level')
        prefer_cost = prefer_cost or ctx.get('prefer_cost')
        tags = tags or ctx.get('tags')
        # 构建参数映射表
        param_map = {
            'temperature': temperature,
            'top_p': top_p,
            'max_tokens': max_tokens,
            'stop': stop
        }
        mapped_params = {k: v for k, v in param_map.items() if v is not None}
        mapped_params.update(kwargs)
        # 优先级1：model_name
        if model_name:
            model_info = next((m for m in self.models if m["name"] == model_name), None)
            if model_info is not None:
                self.current = self.models.index(model_info)
                # 直接调用底层生成逻辑，避免递归
                return self._generate_with_model_info(prompt, model_info, temperature, top_p, max_tokens, stop, **kwargs)
        # 优先级2：preferred_index
        if preferred_index is not None and 0 <= preferred_index < len(self.models):
            self.current = preferred_index
            model_info = self.models[preferred_index]
            return self._generate_with_model_info(prompt, model_info, temperature, top_p, max_tokens, stop, **kwargs)
        # 优先级3：动态分流
        candidates = self._select_llm_candidates(biz_level=biz_level, prefer_cost=prefer_cost, tags=tags)
        if candidates:
            model_info = candidates[0]  # 使用第一个候选模型
            return self._generate_with_model_info(prompt, model_info, temperature, top_p, max_tokens, stop, **kwargs)
        else:
            raise ValueError("No suitable model found")

    def _generate_with_model_info(self, prompt, model_info, temperature=None, top_p=None, max_tokens=None, stop=None, **kwargs):
        """底层生成逻辑，避免递归调用"""
        import uuid
        import time
        from core.statistics import record_model_cost, record_model_call
        
        model_name_for_log = model_info['name']
        request_id = str(uuid.uuid4())
        start = time.time()
        
        print(f"[MultiLLM._generate_with_model_info] 开始处理: model='{model_name_for_log}', prompt='{prompt[:50]}...'", flush=True)
        self.llm_status[model_name_for_log]['current_concurrency'] += 1
        self.llm_status[model_name_for_log]['call_count'] += 1
        
        try:
            client, used_model_name = self._get_sync_client(model_info)
            messages = []
            if temperature is not None or top_p is not None or max_tokens is not None or stop is not None:
                messages.append({"role": "system", "content": f"You are a helpful assistant, your temperature is {temperature}, top_p is {top_p}, max_tokens is {max_tokens}, and stop is {stop}."})
            messages.append({"role": "user", "content": prompt})
            print(f"[MultiLLM._generate_with_model_info] Calling client.chat.completions.create with model '{used_model_name}'...", flush=True)
            t0 = time.time()
            response = client.chat.completions.create(
                model=used_model_name,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stop=stop,
                timeout=10*60
            )
            latency = (time.time() - t0) * 1000  # ms
            s = self.llm_status[model_name_for_log]
            s['latency'] = latency if s['latency'] == 0 else (self.latency_alpha * latency + (1 - self.latency_alpha) * s['latency'])
            self._error_history[model_name_for_log].append(0)
            if len(self._error_history[model_name_for_log]) > self.error_window:
                self._error_history[model_name_for_log].pop(0)
            s['error_rate'] = sum(self._error_history[model_name_for_log]) / len(self._error_history[model_name_for_log])
            content = response.choices[0].message.content
            token_usage = getattr(response, 'usage', None)
            total_tokens = token_usage.total_tokens if token_usage and hasattr(token_usage, 'total_tokens') else None
            model_info2 = next((m for m in self.models if m['name'] == used_model_name), None)
            cost_per_token = model_info2.get('cost', 0.0) if model_info2 else 0.0
            cost = (total_tokens or 0) * cost_per_token if cost_per_token else None
            
            # 记录统计数据
            record_model_cost(model_name_for_log, cost or 0.0)
            record_model_call(model_name_for_log)
            
            logger.info({
                "event": "llm_generate",
                "model": used_model_name,
                "meta": model_info2.get("meta", {}) if model_info2 else {},
                "request_id": request_id,
                "success": True,
                "duration_ms": int((time.time() - start) * 1000),
                "prompt_len": len(prompt),
                "token_usage": total_tokens,
                "cost": cost,
                "params": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens,
                    "stop": stop
                },
            })
            return {
                "result": content,
                "used_model": used_model_name,
                "token_usage": total_tokens,
                "cost": cost
            }
        except Exception as e:
            s = self.llm_status[model_name_for_log]
            self._error_history[model_name_for_log].append(1)
            if len(self._error_history[model_name_for_log]) > self.error_window:
                self._error_history[model_name_for_log].pop(0)
            s['error_rate'] = sum(self._error_history[model_name_for_log]) / len(self._error_history[model_name_for_log])
            s['error_count'] += 1
            logger.error({
                "event": "llm_generate",
                "model": model_name_for_log,
                "meta": model_info.get("meta", {}),
                "request_id": request_id,
                "success": False,
                "duration_ms": int((time.time() - start) * 1000),
                "prompt_len": len(prompt),
                "error": str(e),
                "params": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens,
                    "stop": stop
                },
            })
            raise e
        finally:
            self.llm_status[model_name_for_log]['current_concurrency'] -= 1

    def generate_stream_with_specific_model(self, prompt, model_name=None, temperature=None, top_p=None, max_tokens=None, stop=None, **kwargs):
        """
        OpenAI流式生成器：每次yield一个token或文本片段。
        """
        ctx = llm_context.get({})
        model_name = model_name or ctx.get('model_name')
        temperature = temperature if temperature is not None else ctx.get('temperature')
        top_p = top_p if top_p is not None else ctx.get('top_p')
        max_tokens = max_tokens if max_tokens is not None else ctx.get('max_tokens')
        stop = stop if stop is not None else ctx.get('stop')
        model_info = next((m for m in self.models if m['name'] == model_name), None)
        if model_info is None:
            raise ValueError(f"Model {model_name} not found.")
        
        # 记录调用统计
        from core.statistics import record_model_call
        record_model_call(model_name)
        
        client, used_model_name = self._get_sync_client(model_info)
        messages = []
        messages.append({"role": "user", "content": prompt})
        stream_resp = client.chat.completions.create(
            model=used_model_name,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            stream=True
        )
        for chunk in stream_resp:
            if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0], 'delta'):
                content = chunk.choices[0].delta.content
                if content:
                    yield content




    async def async_generate(self, prompt, model_name=None, temperature=None, top_p=None, max_tokens=None, stop=None, **kwargs):
        ctx = llm_context.get({})
        model_name = model_name or ctx.get('model_name')
        temperature = temperature if temperature is not None else ctx.get('temperature')
        top_p = top_p if top_p is not None else ctx.get('top_p')
        max_tokens = max_tokens if max_tokens is not None else ctx.get('max_tokens')
        stop = stop if stop is not None else ctx.get('stop')
        if model_name:
            return await self.async_generate_with_specific_model(
                prompt=prompt,
                model_name=model_name,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stop=stop,
                **kwargs
            )
        return await self.async_generate_with_auto_model(
            prompt=prompt,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            **kwargs
        )

    async def async_generate_with_specific_model(self, prompt, model_name=None, temperature=None, top_p=None, max_tokens=None, stop=None, **kwargs):
        import uuid
        import time
        from core.statistics import record_model_cost, record_model_call
        
        model_info = next((m for m in self.models if m["name"] == model_name), None)
        if model_info is None:
            raise ValueError(f"Model {model_name} not found.")
        
        model_name_for_log = model_info['name']
        request_id = str(uuid.uuid4())
        start = time.time()
        
        print(f"[MultiLLM.async_generate_with_specific_model] 开始处理: model='{model_name_for_log}', prompt='{prompt[:50]}...'", flush=True)
        self.llm_status[model_name_for_log]['current_concurrency'] += 1
        self.llm_status[model_name_for_log]['call_count'] += 1
        
        try:
            client, used_model_name = await self._get_async_client(model_info)
            messages = []
            if temperature is not None or top_p is not None or max_tokens is not None or stop is not None:
                messages.append({"role": "system", "content": f"You are a helpful assistant, your temperature is {temperature}, top_p = {top_p}, max_tokens = {max_tokens}, and stop = {stop}."})
            messages.append({"role": "user", "content": prompt})
            print(f"[MultiLLM.async_generate_with_specific_model] Calling client.chat.completions.create with model '{used_model_name}'...", flush=True)
            t0 = time.time()
            response = await client.chat.completions.create(
                model=used_model_name,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stop=stop,
            )
            latency = (time.time() - t0) * 1000  # ms
            s = self.llm_status[model_name_for_log]
            s['latency'] = latency if s['latency'] == 0 else (self.latency_alpha * latency + (1 - self.latency_alpha) * s['latency'])
            self._error_history[model_name_for_log].append(0)
            if len(self._error_history[model_name_for_log]) > self.error_window:
                self._error_history[model_name_for_log].pop(0)
            s['error_rate'] = sum(self._error_history[model_name_for_log]) / len(self._error_history[model_name_for_log])
            content = response.choices[0].message.content
            token_usage = getattr(response, 'usage', None)
            total_tokens = token_usage.total_tokens if token_usage and hasattr(token_usage, 'total_tokens') else None
            model_info2 = next((m for m in self.models if m['name'] == used_model_name), None)
            cost_per_token = model_info2.get('cost', 0.0) if model_info2 else 0.0
            cost = (total_tokens or 0) * cost_per_token if cost_per_token else None
            
            # 记录统计数据
            record_model_cost(model_name_for_log, cost or 0.0)
            record_model_call(model_name_for_log)
            
            logger.info({
                "event": "llm_generate",
                "model": used_model_name,
                "meta": model_info2.get("meta", {}) if model_info2 else {},
                "request_id": request_id,
                "success": True,
                "duration_ms": int((time.time() - start) * 1000),
                "prompt_len": len(prompt),
                "token_usage": total_tokens,
                "cost": cost,
                "params": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens,
                    "stop": stop
                },
            })
            
            return {
                "result": content,
                "used_model": used_model_name,
                "token_usage": total_tokens,
                "cost": cost
            }
        except Exception as e:
            s = self.llm_status[model_name_for_log]
            self._error_history[model_name_for_log].append(1)
            if len(self._error_history[model_name_for_log]) > self.error_window:
                self._error_history[model_name_for_log].pop(0)
            s['error_rate'] = sum(self._error_history[model_name_for_log]) / len(self._error_history[model_name_for_log])
            s['error_count'] += 1
            logger.error({
                "event": "llm_generate",
                "model": model_name_for_log,
                "meta": model_info.get("meta", {}),
                "request_id": request_id,
                "success": False,
                "duration_ms": int((time.time() - start) * 1000),
                "prompt_len": len(prompt),
                "error": str(e),
                "params": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens,
                    "stop": stop
                },
            })
            raise e
        finally:
            self.llm_status[model_name_for_log]['current_concurrency'] -= 1

    async def async_generate_with_auto_model(self, prompt, temperature=None, top_p=None, max_tokens=None, stop=None, **kwargs):
        ctx = llm_context.get({})
        model_name = ctx.get('model_name')
        biz_level = ctx.get('biz_level')
        prefer_cost = ctx.get('prefer_cost')
        tags = ctx.get('tags')
        candidates = self._select_llm_candidates(model_name=model_name, biz_level=biz_level, prefer_cost=prefer_cost, tags=tags)
        last_exception = None
        for model_info in candidates:
            try:
                return await self.async_generate_with_specific_model(
                    prompt=prompt,
                    model_name=model_info['name'],
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    stop=stop,
                    **kwargs
                )
            except Exception as e:
                last_exception = e
                continue
        raise last_exception or Exception("All model attempts failed.") 