import requests

articles_ = [
    {"content": "6月28日，国有企业A发布公告称，完成对B公司的重组，成为其控股股东。此次重组涉及资金10亿元。业内专家李明认为，此次重组有助于提升企业核心竞争力，推动国有企业改革。B公司主要从事新能源和高端装备制造业务。", "title": "标题1", "author": "张三"},
    {"content": "B公司近日又获得一项新能源领域的重大技术突破，预计将进一步提升其市场份额。", "title": "标题2", "author": "李四"},
    {"content": "专家李明表示，未来国有企业在数字经济领域也将有更大作为。", "title": "标题3", "author": "王五"}
]

batch_payload = [{"article": doc["content"]} for doc in articles_]

PLUGIN_INVOKE_URL = "http://127.0.0.1:8000/plugin/invoke"
plugin_name = "extract_"
PREFERRED_MODEL_NAME = "GLM-4-Flash"  # 请替换为实际可用模型名

with requests.Session() as s:
    # 1. 先设置 session 绑定的优先模型
    set_resp = s.post("http://127.0.0.1:8000/set_preferred_model", json={
        "model_name": PREFERRED_MODEL_NAME
    })
    set_data = set_resp.json()
    print("设置优先模型结果:", set_data)
    session_id = set_data.get("session_id")
    print(f"session_id: {session_id}")

    # 2. 用该 session 进行批量插件调用
    headers = {}
    if session_id:
        headers["Cookie"] = f"session_id={session_id}"
    resp = s.post(
        f"{PLUGIN_INVOKE_URL}?plugin_name={plugin_name}",
        json={
            "batch_payload": batch_payload
        },
        headers=headers
    )
    data = resp.json()

    if "results" in data:
        print("批量返回结果：")
        for idx, res in enumerate(data["results"]):
            print(f"第{idx+1}个文档结果：", res)
    else:
        print("API返回异常：", data)
    print("--- 多文档批量调用结束 ---") 