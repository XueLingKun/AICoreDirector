import requests
import time

# 构造足够多的测试数据，超过单 LLM 并发上限（如每个 LLM qps=2，这里发10条）
articles_ = [
    {"content": f"测试文本 {i+1}"} for i in range(10)
]

batch_payload = [{"article": doc["content"]} for doc in articles_]
PLUGIN_INVOKE_URL = "http://127.0.0.1:8000/plugin/invoke"
plugin_name = "extract_"

start = time.time()
resp = requests.post(
    f"{PLUGIN_INVOKE_URL}?plugin_name={plugin_name}",
    json={
        "batch_payload": batch_payload
    }
)
data = resp.json()
end = time.time()

print(f"\n--- LLM 智能分流测试 ---")
print(f"总耗时: {end - start:.2f} 秒")
if "results" in data:
    used_models = {}
    for idx, res in enumerate(data["results"]):
        # 假设后端返回结构中包含 used_model 字段
        model = res.get("used_model", "未知")
        used_models.setdefault(model, 0)
        used_models[model] += 1
        print(f"第{idx+1}个文档结果：模型={model}，结果={res.get('result', res)}")
    print("\n各模型命中统计：")
    for m, cnt in used_models.items():
        print(f"{m}: {cnt} 条")
else:
    print("API返回异常：", data)
print("--- 测试结束 ---\n") 