import os, re, json
# from dotenv import load_dotenv
import configparser
from adapters.llm_adapter import MultiLLM
import asyncio
import ast # 导入ast模块

# 加载prompt.ini
config = configparser.ConfigParser()
config.read('config_prompts/prompt.ini', encoding='utf-8')


# 延迟初始化LLM实例，避免在模块导入时创建重复实例
_llm_instance = None

def get_llm_instance():
    global _llm_instance
    if _llm_instance is None:
        try:
            from api.main import llm_manager
            if llm_manager is not None:
                _llm_instance = llm_manager
            else:
                # 如果llm_manager为None，创建新实例
                _llm_instance = MultiLLM()
        except ImportError:
            # 如果无法导入，则创建新实例
            _llm_instance = MultiLLM()
    return _llm_instance

# 为了兼容现有代码，提供一个llm变量
llm = None

# Import the session_preferred_models dictionary from api_server to access session preferences
# Note: This creates tight coupling. In a larger app, consider a shared state manager or passing state.
# from api_server import session_preferred_models # Import the shared dictionary

async def extract_info(article: str) -> dict:
    prompt_ = config.get('extractor_prompt', 'prompt')
    prompt_ = prompt_.replace("{article}", article)
    try:
        llm_instance = get_llm_instance()
        content_dict = await llm_instance.async_generate(prompt_)
        print("llm.async_generate(prompt_) 返回类型：", type(content_dict), content_dict)
        content = content_dict.get("result", "")
    except Exception as e:
        print("大模型API调用失败：", e)
        return {"error": str(e)}
    print("原始返回内容：", content)
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)
    try:
        judge_result = json.loads(content)
    except Exception:
        judge_result = {"score": 0, "advice": "无法解析评分结果，请检查格式。"}
    return judge_result

def extract_info_async(article: str) -> dict:
    prompt_ = config.get('extractor_prompt', 'prompt')
    prompt_ = prompt_.replace("{article}", article)
    print("最终发送给模型的prompt：", prompt_)
    async def _inner():
        try:
            llm_instance = get_llm_instance()
            content = await llm_instance.async_generate(prompt_)
        except Exception as e:
            print("大模型API异步调用失败：", e)
            return {"error": str(e)}
        print("原始返回内容：", content)
        content_ = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)
        try:
            judge_result = json.loads(content_)
        except Exception:
            judge_result = {"score": 0, "advice": "无法解析评分结果，请检查格式。"}
        return judge_result
    return _inner()

def extract_info_with_history(
    article: str,
    session_id: str,
    history: list,
    system_prompt: str | None = None,
    user_prompt_template: str | None = None,
    preferred_index: int | None = None
) -> dict:
    print(f"[extract_info_with_history] 开始处理 session_id: {session_id}", flush=True)

    # Retrieve the preferred model index for this session
    # preferred_index = session_preferred_models.get(session_id)
    print(f"[extract_info_with_history] Retrieved preferred_index for session {session_id}: {preferred_index}", flush=True)

    llm_instance = get_llm_instance()
    # Store the original current model index
    original_current_index = llm_instance.current
    used_preferred_model = False

    try:
        # If a preferred index is found and is different from the current global model
        if preferred_index is not None and preferred_index != original_current_index:
            # Temporarily set the global current model to the preferred index
            llm_instance.current = preferred_index
            used_preferred_model = True
            print(f"[extract_info_with_history] Temporarily set llm.current to preferred_index: {llm_instance.current}", flush=True)

        # Determine the system prompt to use
        final_system_prompt = system_prompt

        # Determine the user prompt template to use
        if user_prompt_template is not None:
            final_user_prompt_template = user_prompt_template
            print("[extract_info_with_history] Using provided user_prompt_template.", flush=True)
        else:
            final_user_prompt_template = config.get('extractor_prompt', 'prompt')
            print("[extract_info_with_history] Using default user_prompt_template from prompt.ini.", flush=True)

        # Build history dialogue string
        history_str = ""
        if history:
            history_str += "\n请参考下面的对话历史，并结合当前提供的资讯，完成抽取：\n\n"
            for msg in history:
                history_str += f"{msg['role']}: {str(msg['content'])}\n"
            history_str += "\n"

        # Combine final user prompt from template, history, and current article
        if "{article}" in final_user_prompt_template:
             user_prompt_content = final_user_prompt_template.replace("{article}", history_str + f"当前要抽取的资讯原文如下：\n{article}")
        else:
            user_prompt_content = final_user_prompt_template + history_str + f"当前要抽取的资讯原文如下：\n{article}"

        print("[extract_info_with_history] Final user prompt content for model:\n---\n" + user_prompt_content + "\n---\n", flush=True)

        # Implement retry logic here
        max_retries = len(llm_instance.models)
        last_exception = None

        for attempt in range(max_retries):
            try:
                print(f"[extract_info_with_history] Attempt {attempt + 1}/{max_retries}: Calling llm.generate with current model (Index: {llm_instance.current})...", flush=True)
                # Call llm.generate without model_index parameter
                content = llm_instance.generate(
                    prompt=user_prompt_content,
                    system_prompt=final_system_prompt,
                )
                print("[extract_info_with_history] llm.generate call completed successfully.", flush=True)

                # If successful, break the retry loop
                break

            except Exception as e:
                last_exception = e
                print(f"[extract_info_with_history] Attempt {attempt + 1}/{max_retries}: LLM API call failed with current model (Index: {llm_instance.current}): {e}", flush=True)
                # On failure, switch to the next model for the next attempt
                if attempt < max_retries - 1:
                    print(f"[extract_info_with_history] Switching to next model using llm._next()...", flush=True)
                    llm_instance._next()

        # If the loop completes without success, raise the last exception
        else:
            print("[extract_info_with_history] All retry attempts failed.", flush=True)
            raise last_exception or Exception("All model attempts failed.")

        print("[extract_info_with_history] Raw response content:\n---\n" + content + "\n---\n", flush=True)

        # More robust JSON extraction: find the first '{' or '[' and the last '}' or ']'
        json_start = -1
        json_end = -1

        # Find the first opening brace or bracket
        for i, char in enumerate(content):
            if char == '{' or char == '[':
                json_start = i
                break

        # Find the last closing brace or bracket, searching forwards from the start
        # This balance-based approach is better for nested structures
        if json_start != -1:
            balance = 0
            for i in range(json_start, len(content)):
                if content[i] == '{' or content[i] == '[':
                    balance += 1
                elif content[i] == '}' or content[i] == ']':
                    balance -= 1

                # If balance is zero and we see a closing character matching the potential root level
                # This assumes the main JSON structure is at the outermost level found
                if balance == 0 and (content[i] == '}' or content[i] == ']'):
                    json_end = i + 1 # Include the closing character
                    # Optional: could continue searching for the absolute last closing char if needed
                    # but breaking here assumes the first balanced structure is the target.
                    # If nested JSON is expected at the top level, this needs adjustment.
                    # For typical single JSON object/array output, this should work.
                    # To be safer, let's continue to find the absolute last balanced structure
                    # Store potential end and keep searching
                    # json_end = i + 1 # Store potential end
                    pass # Continue search to find the last one

            # After the forward pass, json_end will hold the end of the last balanced structure found
            # If balance is still not zero, the JSON is likely malformed or incomplete
            if balance != 0 or json_end == -1:
                print("[extract_info_with_history] Warning: JSON balance mismatch or end not found by balancing. JSON may be incomplete or malformed.", flush=True)
                # In case of malformed JSON, json_end might still be -1 or point to an incomplete structure
                # As a fallback, we can try finding the absolute last closing brace/bracket again,
                # but the balance check is a stronger indicator of a valid structure.
                # Let's rely on the balance check and potentially fail if not balanced.
                # If balance != 0, it's likely not valid JSON anyway.
                pass # No fallback to last brace/bracket if balance is off, rely on balance

        if json_start != -1 and json_end != -1 and json_end > json_start:
            # Extract the potential JSON string
            potential_json_str = content[json_start:json_end]
            print("[extract_info_with_history] Extracted potential JSON content based on braces/brackets:", potential_json_str, flush=True)

            # Further clean by stripping leading/trailing whitespace and potentially problematic non-JSON characters
            # This regex tries to match leading/trailing whitespace and non-brace/bracket characters
            # It's complex and might need adjustment based on actual model outputs
            # A simpler approach: just strip whitespace after extraction
            content_ = potential_json_str.strip()
            print("[extract_info_with_history] Trimmed whitespace after extraction:", content_, flush=True)

            # Optional: More aggressive cleaning if still failing, e.g., remove characters before first '{' or '['
            # import re
            # match = re.search(r'[{[\].*?}[\]]', content, re.DOTALL)
            # if match:
            #    content_ = match.group(0)
            # else:
            #    content_ = potential_json_str.strip()

        else:
            # If no clear JSON structure found by braces/brackets, fall back to markdown cleaning
            print("[extract_info_with_history] No clear JSON structure found based on braces/brackets. Falling back to markdown cleaning.", flush=True)
            content_ = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)

        # print("[extract_info_with_history] Cleaned content:\n---\n" + content_ + "\n---\n", flush=True) # Original print
        print("[extract_info_with_history] Final content for parsing:\n---\n" + content_ + "\n---\n", flush=True)

        try:
            print("[extract_info_with_history] Attempting JSON parse...", flush=True)
            judge_result = json.loads(content_)
            print("[extract_info_with_history] JSON parse successful.", flush=True)
        except Exception as json_e:
            print(f"[extract_info_with_history] JSON parse failed: {json_e}. Attempting ast.literal_eval...", flush=True)
            try:
                judge_result = ast.literal_eval(content_)
                print("[extract_info_with_history] ast.literal_eval parse successful.", flush=True)
            except Exception as e_ast:
                print("[extract_info_with_history] ast.literal_eval parse also failed:", e_ast, flush=True)
                # Return a structured error indicating parsing failure
                judge_result = {"score": 0, "advice": "无法解析模型返回结果，请检查格式。", "error": f"Parsing Error: JSON failed with '{str(json_e)}', literal_eval failed with '{str(e_ast)}'. Content: '{content_[:100]}...'"}

        print("[extract_info_with_history] Returning result:", judge_result, flush=True)
        return judge_result
    finally:
        # Restore the original current model index
        if used_preferred_model:
            llm_instance.current = original_current_index

if __name__ == "__main__":
    article = """
6月28日，国有企业A发布公告称，完成对B公司的重组，成为其控股股东。此次重组涉及资金10亿元。业内专家李明认为，此次重组有助于提升企业核心竞争力，推动国有企业改革。B公司主要从事新能源和高端装备制造业务.
"""
    # 同步调用示例 (使用 MultiLLM 内部的重试和切换逻辑)
    print("\n--- 同步调用示例 ---", flush=True)
    try:
        # You can test preferred_index here by passing a valid index
        llm_instance = get_llm_instance()
        result = llm_instance.generate(prompt="请分析以下资讯并提取信息：" + article, preferred_index=0) # Example with preferred_index=0
        print("同步调用结果：", result)
    except Exception as e:
        print("同步调用失败：", e)

    # 异步调用示例 (使用 MultiLLM 内部的重试和切换逻辑)
    async def async_main():
        print("\n--- 异步调用示例 ---", flush=True)
        try:
             # You can test preferred_index here by passing a valid index
            llm_instance = get_llm_instance()
            result_async = await llm_instance.async_generate(prompt="请分析以下资讯并提取信息：" + article, preferred_index=1) # Example with preferred_index=1
            print("异步调用结果：", result_async)
        except Exception as e:
            print("异步调用失败：", e)

    # 为了在 __main__ 中运行 async main，使用 asyncio.run()
    try:
        # Re-check if llm was initialized successfully before running async part
        llm_instance = get_llm_instance()
        if llm_instance and llm_instance.models:
            asyncio.run(async_main())
        else:
            print("LLM 初始化失败或没有可用模型，跳过异步示例。", flush=True)
    except Exception as e:
        print(f"异步主函数运行失败: {e}", flush=True)
