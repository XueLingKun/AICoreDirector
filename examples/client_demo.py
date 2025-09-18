import requests

API_URL_STATEFUL = "http://127.0.0.1:8000/extract_stateful" # 有状态接口
API_URL_STATELESS = "http://127.0.0.1:8000/extract_" # 无状态接口

# 模拟多轮对话
articles_ = [
    {"content": "6月28日，国有企业A发布公告称，完成对B公司的重组，成为其控股股东。此次重组涉及资金10亿元。业内专家李明认为，此次重组有助于提升企业核心竞争力，推动国有企业改革。B公司主要从事新能源和高端装备制造业务。", "title": "标题1", "author": "张三"},
    {"content": "B公司近日又获得一项新能源领域的重大技术突破，预计将进一步提升其市场份额。", "title": "标题2", "author": "李四"},
    {"content": "专家李明表示，未来国有企业在数字经济领域也将有更大作为。", "title": "标题3", "author": "王五"}
]

# articles = [
#     {"content": "位于北京市房山区良乡卫星城的一个大型污水处理厂里，经过处理的中水清澈见底、没有异味，鱼儿欢快地游动……该污水处理厂是中冶集团下属企业中国恩菲获得的第一个特许经营协议（BOT）投资项目，二期建设规模4万吨日，近期将正式竣工通水。如今，随着越来越多的大型央企掘金环保行业，中国环保行业企业规模偏小、分散，资金不足，技术水平也不够成熟的格局正在改变。央企依靠深厚的技术积淀，在固废处理、污水处理、烟尘治理、脱硫等领域掌握大量环保核心技术，大大提升了行业技术水平，缩短了中国环保技术与欧美国家的差距。以央企唯一主业为节能减排、环保的中国节能集团为例，该企业以BOT等模式投资建设了生物质能发电、污泥发电等一批固废环保项目，总投资近百亿元，目前已在全国16个省份30余个城市投建固废综合处理项目近50个，日均固废处理量占到全国固废处理总量的10。而以水务领域为例，中冶集团子公司中冶华天已通过BOT、TOT等模式先后投资运营了19个市政污水处理项目。未来将央企的品牌与技术优势和民企的活力相结合，在产业内形成完整成熟的产业链条，可以有效促进节能环保产业结构的转型升级。中国企业改革与发展研究会副会长李锦则认为，节能环保领域未来可以走"央企民企"的新型商业模式。据了解，不少进入环保产业的央企已在积极尝试"混改"之路。中国节能副总经理张超认为，节能环保行业并不是垄断行业，国资、民资、外资都将参与其中。目前中国节能在境外的3家上市公司均有外资进入，多个二级子公司或项目公司中也有不少地方国资与民资合作方。张超表示，未来公司会按照国家政策继续积极引入社会资本。", "title": "标题3", "author": "王五"}
# ]





# # --- 有状态调用示例 (手动管理 cookie) ---
# # 无需requests.Session()

# print("--- 开始有状态调用 (手动管理cookie) ---")
# session_id = None # 初始化 session_id

# for idx, doc in enumerate(articles):
#     print(f"\n发送第{idx+1}轮请求...")
#     headers = {'Content-Type': 'application/json'}
#     # 如果已经有了session_id，添加到Cookie头部
#     if session_id:
#         headers['Cookie'] = f'session_id={session_id}'
#         print("发送Cookie Header:", headers['Cookie'])

#     resp = requests.post(API_URL_STATEFUL, json={"article": doc["content"]}, headers=headers)

#     data = resp.json()
#     print(f"第{idx+1}轮（有状态）调用结果：")
#     print("返回结果：", data["result"])

#     # 从返回数据中获取新的session_id (第一次请求时服务器会返回)
#     # 并且更新本地存储的session_id
#     if "session_id" in data and data["session_id"] != session_id:
#         session_id = data["session_id"]
#         print("从服务端获取并更新session_id为:", session_id)

#     print("-")
# print("--- 有状态调用结束 ---")





# --- 无状态调用示例 (独立请求，不管理cookie) ---
# print("\n--- 开始无状态调用 (已注释) ---")
# for idx, doc in enumerate(articles_):
#     # 注意这里调用的是无状态接口
#     print(type(doc["content"]), doc["content"])
#     resp = requests.post(API_URL_STATELESS, json={"article": doc["content"]})
#     data = resp.json()
#     print(f"第{idx+1}轮（无状态）调用：")
#     if "result" in data:
#         print("返回结果：", data["result"])
#     else:
#         print("API返回异常：", data)
#     print("-")
# print("--- 无状态调用结束 ---")

# --- 多文档批量调用API示例 ---
print("\n--- 开始多文档批量调用 ---")
# 构造 batch_payload，每条为 {"article": ...}
batch_payload = [{"article": doc["content"]} for doc in articles_]

PLUGIN_INVOKE_URL = "http://127.0.0.1:8000/plugin/invoke"
plugin_name = "extract_"  # 需与后端注册插件名一致

resp = requests.post(
    f"{PLUGIN_INVOKE_URL}?plugin_name={plugin_name}",
    json={
        "batch_payload": batch_payload
    }
)
data = resp.json()

if "results" in data:
    print("批量返回结果：")
    for idx, res in enumerate(data["results"]):
        print(f"第{idx+1}个文档结果：", res)
else:
    print("API返回异常：", data)
print("--- 多文档批量调用结束 ---")

# resp = requests.post("http://127.0.0.1:8000/list_models")
# data = resp.json()
# # print("返回结果：", data)

# # Print the correct information from /list_models endpoint
# print("--- Available Models ---")
# for model in data.get("available_models", []):
#     print(f"Index: {model['index']}, Name: {model['name']}")
# print("----------------------")
# print(f"Current Global Model Index: {data.get('current_global_model_index')}")
# print(f"Current Global Model Name: {data.get('current_global_model_name')}")
# print("----------------------")


# # --- 调用 /set_preferred_model 示例 ---
# try:
#     # 首先使用 /list_models 获取可用模型信息，选择一个模型的 name
#     # resp_list = requests.post("http://127.0.0.1:8000/list_models")
#     # models_info = resp_list.json()
#     # print("Available models for setting preferred:", models_info)

#     # 假设你想将模型名为 "YourPreferredModelName" 的模型设为优先
#     # 请替换为实际可用的模型名称
#     preferred_model_name = "GLM-4-Flash"

#     print(f"\n--- 尝试设置优先模型为: {preferred_model_name} ---")
#     # Use requests.Session() to maintain session_id
#     with requests.Session() as s:
#         # Add print statement before set_preferred_model call
#         print(f"[client_demo] Session ID in client before set_preferred_model: {s.cookies.get('session_id')}", flush=True)
#         # Set preferred model
#         set_resp = s.post("http://127.0.0.1:8000/set_preferred_model", json={
#             "model_name": preferred_model_name
#             # "model_url": "...", # Optional, not used by server for now
#             # "model_key": "..."  # Optional, not used by server for now
#         })
#         set_data = set_resp.json()
#         print("设置优先模型结果:", set_data)

#         if set_resp.status_code == 200:
#             print(f"优先模型设置成功。 session_id: {set_data.get('session_id')}")
#             # Add print statement to confirm session ID in client after setting preference
#             print(f"[client_demo] Session ID after set_preferred_model: {s.cookies.get('session_id')}", flush=True)
#             # 此时再调用 /extract 就会优先使用设置的模型
#             print("\n--- 使用设置的优先模型进行抽取 ---")
#             # Add print statement before extract call
#             print(f"[client_demo] Session ID in client before extract: {s.cookies.get('session_id')}", flush=True)
#             extract_resp = s.post(API_URL_STATEFUL, json={"article": articles[0]["content"]})
#             extract_data = extract_resp.json()
#             print("使用优先模型抽取结果:", extract_data["result"])

# except Exception as e:
#     print(f"设置优先模型或抽取失败: {e}")


# # --- 调用 /extract_with_prompt 示例 ---
# print("\n--- 调用 /extract_with_prompt 示例 ---")

# # Custom prompts requesting JSON output
# custom_system_prompt = "你是一个文档信息提取和摘要专家。请严格按照以下JSON格式输出对文档的分析结果，不包含任何额外文字、Markdown格式或解释说明：{\"key_info\": \"string\"}。key_info应包含从文档中提取的关键信息和摘要。请使用中文。"
# custom_user_prompt_template = "请分析以下文档：{article}"

# article_for_custom_prompt = """
# 特斯拉CEO埃隆·马斯克今天宣布，公司最新款电动汽车Model Z已开始接受预订，预计明年上半年交付。Model Z定位于紧凑型SUV市场，起售价为3万美元，续航里程预计可达400公里。此举被认为是特斯拉进一步拓展大众市场的关键一步。
# """

# try:
#     # 使用 requests.Session() 来维护 session_id 和优先模型设置 (如果之前设置过)
#     with requests.Session() as s:
#         print("发送带自定义prompt的抽取请求...")
#         prompt_resp = s.post("http://127.0.0.1:8000/extract_with_prompt", json={
#             "article": article_for_custom_prompt,
#             "system_prompt": custom_system_prompt, # 可选
#             "user_prompt_template": custom_user_prompt_template # 可选
#         })
#         prompt_data = prompt_resp.json()

#         print("\n/extract_with_prompt 调用结果:")
#         print("返回数据:", prompt_data)

#         # 如果需要多轮对话，可以继续使用同一个session对象 s 发送请求

# except Exception as e:
#     print(f"调用 /extract_with_prompt 失败: {e}")

