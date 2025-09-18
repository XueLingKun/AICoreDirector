from typing import List, Optional
import random

class ModelRouter:
    def __init__(self, get_models):
        self.get_models = get_models  # 函数，返回模型列表

    def select_model(self, tags: Optional[List[str]] = None, biz_level: Optional[str] = None, prefer_cost: Optional[str] = None, **kwargs):
        models = self.get_models()
        # 1. 只选健康模型
        candidates = [m for m in models if m.get('health', 'healthy') == 'healthy' and m.get('meta', {}).get('status', '可用') == '可用']
        # 2. 标签/能力匹配
        if tags:
            candidates = [m for m in candidates if set(tags).issubset(set(m.get('meta', {}).get('tags', [])))]
        # 3. 业务等级优先
        if biz_level == 'premium':
            # 高价值业务优先选高成本（效果好）、QPS高的模型
            candidates = sorted(candidates, key=lambda m: (-m.get('meta', {}).get('cost', 0), -m.get('meta', {}).get('qps', 0)))
        elif biz_level == 'economy':
            # 经济型业务等同于成本优先低
            prefer_cost = 'low'
        elif biz_level == 'normal':
            # 普通业务优先选性价比
            candidates = sorted(candidates, key=lambda m: (m.get('meta', {}).get('cost', 0), -m.get('meta', {}).get('qps', 0)))
        # 4. 成本偏好
        if prefer_cost == 'low':
            candidates = sorted(candidates, key=lambda m: m.get('meta', {}).get('cost', 0))
        elif prefer_cost == 'high':
            candidates = sorted(candidates, key=lambda m: -m.get('meta', {}).get('cost', 0))
        # 5. 兜底：随机/轮询
        if not candidates:
            raise Exception('No suitable model available')
        return candidates[0] 