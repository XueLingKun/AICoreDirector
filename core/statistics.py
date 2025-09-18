from datetime import datetime

# 内存统计数据
model_hit_counter = {}
model_cost_counter = {}
model_cost_counter_user_app = {}
total_request_count = 0
model_call_history = []

def record_model_call(model_name):
    """记录模型调用"""
    global model_hit_counter, total_request_count
    model_hit_counter[model_name] = model_hit_counter.get(model_name, 0) + 1
    total_request_count += 1
    model_call_history.append({
        "model": model_name,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    # 限制历史记录数量，避免内存过大
    if len(model_call_history) > 10000:
        model_call_history.pop(0)
    print(f"[统计] 记录模型调用: {model_name}, 当前命中次数: {model_hit_counter[model_name]}")
    print(f"[统计] 当前总请求数: {total_request_count}")

def record_model_cost(model_name, cost):
    """记录模型成本"""
    global model_cost_counter
    model_cost_counter[model_name] = model_cost_counter.get(model_name, 0.0) + cost
    print(f"[统计] 记录模型成本: {model_name}, 成本: {cost}, 累计成本: {model_cost_counter[model_name]}")

def record_model_cost_user_app(model_name, user_id, app_id, cost):
    """记录用户应用维度的模型成本"""
    global model_cost_counter_user_app
    key = (model_name, user_id or "", app_id or "")
    model_cost_counter_user_app[key] = model_cost_counter_user_app.get(key, 0.0) + cost
    print(f"[统计] 记录用户应用成本: {key}, 成本: {cost}, 累计成本: {model_cost_counter_user_app[key]}") 