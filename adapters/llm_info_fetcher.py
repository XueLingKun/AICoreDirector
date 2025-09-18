import requests
import yaml
import json
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

"""
llm_info_fetcher.py
==================

多厂商LLM信息适配与同步工具。

【如何扩展新厂商适配器】
-------------------------
1. 新建一个继承自 LLMProviderAdapter 的类，实现以下方法：
   - fetch_cost_info(self) -> Dict[str, Any]
   - fetch_balance(self) -> Optional[float]
   - get_name(self) -> str
2. 在 adapters 字典中注册你的新适配器。

【示例】
-------
class ZhipuAdapter(LLMProviderAdapter):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def fetch_cost_info(self) -> Dict[str, Any]:
        # 这里应实现抓取或API获取智谱价格的逻辑
        return {
            "glm-4": {
                "input_price": 0.012,
                "output_price": 0.036
            }
        }

    def fetch_balance(self) -> Optional[float]:
        # 这里应实现API获取智谱余额的逻辑
        return None

    def get_name(self) -> str:
        return "zhipu"

# 注册到adapters:
adapters = {
    "deepseek-reasoner": DeepSeekAdapter(api_key=None),
    "openai": OpenAIAdapter(api_key=None),
    "zhipu": ZhipuAdapter(api_key=None),
}

"""

# =====================
# LLM Provider Adapter Interface
# =====================
class LLMProviderAdapter(ABC):
    @abstractmethod
    def fetch_cost_info(self) -> Dict[str, Any]:
        """获取LLM厂商的cost/价格信息"""
        pass

    @abstractmethod
    def fetch_balance(self) -> Optional[float]:
        """获取LLM厂商的余额信息（如支持）"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """返回厂商名称/唯一标识"""
        pass

# =====================
# DeepSeek Adapter
# =====================
class DeepSeekAdapter(LLMProviderAdapter):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def fetch_cost_info(self) -> Dict[str, Any]:
        url = "https://api-docs.deepseek.com/quick_start/pricing-details-usd"
        resp = requests.get(url)
        if resp.status_code != 200:
            raise Exception("Failed to fetch DeepSeek pricing page")
        html = resp.text
        import re
        pattern = re.compile(r'deepseek-reasoner.*?\|\s*(\d+K).*?\|\s*(\d+K).*?\|\s*(\d+K).*?\|\s*\$(\d+\.\d+).*?\|\s*\$(\d+\.\d+).*?\|\s*\$(\d+\.\d+)', re.DOTALL)
        m = pattern.search(html)
        if not m:
            raise Exception("Failed to parse DeepSeek pricing table")
        return {
            "context_length": m.group(1),
            "max_cot_tokens": m.group(2),
            "max_output_tokens": m.group(3),
            "input_price_cache_hit": float(m.group(4)),
            "input_price_cache_miss": float(m.group(5)),
            "output_price": float(m.group(6)),
        }

    def fetch_balance(self) -> Optional[float]:
        if not self.api_key:
            return None
        url = "https://api.deepseek.com/v1/dashboard/billing/credit"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("credit", None)

    def get_name(self) -> str:
        return "deepseek-reasoner"

# =====================
# OpenAI Adapter (结构示例)
# =====================
class OpenAIAdapter(LLMProviderAdapter):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def fetch_cost_info(self) -> Dict[str, Any]:
        # 示例：OpenAI价格通常需手动维护或爬取官网
        # 这里返回一个静态示例，实际可扩展为爬取或API获取
        return {
            "gpt-4-turbo": {
                "input_price": 0.01,  # $/1K tokens
                "output_price": 0.03
            },
            "gpt-3.5-turbo": {
                "input_price": 0.0005,
                "output_price": 0.0015
            }
        }

    def fetch_balance(self) -> Optional[float]:
        if not self.api_key:
            return None
        url = "https://api.openai.com/dashboard/billing/credit_grants"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("total_available", None)

    def get_name(self) -> str:
        return "openai"

# =====================
# LLM Info Fetcher (统一调度)
# =====================
class LLMInfoFetcher:
    def __init__(self, adapters: Dict[str, LLMProviderAdapter]):
        self.adapters = adapters
        self.llm_info: Dict[str, Any] = {}

    def refresh_all(self):
        for name, adapter in self.adapters.items():
            try:
                cost = adapter.fetch_cost_info()
                balance = adapter.fetch_balance()
                self.llm_info[name] = {
                    "cost": cost,
                    "balance": balance,
                    "last_update": datetime.now().isoformat()
                }
                print(f"[{name}] cost/balance信息已刷新.")
            except Exception as e:
                print(f"[{name}] 刷新失败: {e}")

    def save_to_yaml(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.llm_info, f, allow_unicode=True)

    def save_to_json(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.llm_info, f, indent=2, ensure_ascii=False)

    def update_llm_models_yaml(self, models_yaml_path: str):
        # 读取现有llm_models.yaml，更新cost/balance等字段
        try:
            with open(models_yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception:
            data = {"models": []}
        models = data.get("models", data if isinstance(data, list) else [])
        for m in models:
            name = m.get("name")
            if name and name in self.llm_info:
                if "meta" not in m:
                    m["meta"] = {}
                m["meta"]["cost_info"] = self.llm_info[name]["cost"]
                m["meta"]["balance"] = self.llm_info[name]["balance"]
                m["meta"]["last_update"] = self.llm_info[name]["last_update"]
        # 写回
        if isinstance(data, dict) and "models" in data:
            data["models"] = models
        else:
            data = models
        with open(models_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

# =====================
# Example Usage
# =====================
if __name__ == "__main__":
    # 可根据需要传入API Key
    adapters = {
        "deepseek-reasoner": DeepSeekAdapter(api_key=None),
        "openai": OpenAIAdapter(api_key=None),
        # 后续可扩展更多厂商: "zhipu": ZhipuAdapter(...)
    }
    fetcher = LLMInfoFetcher(adapters)
    fetcher.refresh_all()
    # 保存到单独的yaml/json
    fetcher.save_to_yaml("llm_costs.yaml")
    fetcher.save_to_json("llm_costs.json")
    # 更新到llm_models.yaml（如有）
    fetcher.update_llm_models_yaml("../llm_models.yaml") 