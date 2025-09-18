from core.plugin_loader import plugin_api
from business.doc_extractor import extract_info_with_history, extract_info, llm
from core.state_manager import state_manager
import uuid
from adapters.llm_adapter import llm_context

@plugin_api
def extract_stateful(article: str, session_id: str = None) -> dict:
    """
    插件API：带会话的抽取。
    """
    # 会话ID自动生成（如未传）
    if not session_id:
        session_id = str(uuid.uuid4())
    history = state_manager.get_history(session_id)
    preferred_index = state_manager.get_preferred_model_index(session_id)
    try:
        result = extract_info_with_history(article, session_id, history, preferred_index=preferred_index)
        history.append({"role": "user", "content": article})
        if "error" not in result:
            history.append({"role": "assistant", "content": str(result)})
        state_manager.update_history(session_id, history)
        return {"result": result, "session_id": session_id}
    except Exception as e:
        return {"error": "Extraction failed", "details": str(e), "session_id": session_id}

@plugin_api
def extract_with_prompt(article: str, system_prompt: str = None, user_prompt_template: str = None, session_id: str = None) -> dict:
    """
    插件API：带自定义Prompt的抽取。
    """
    if not session_id:
        session_id = str(uuid.uuid4())
    history = state_manager.get_history(session_id)
    preferred_index = state_manager.get_preferred_model_index(session_id)
    try:
        result = extract_info_with_history(
            article, session_id, history,
            preferred_index=preferred_index,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template
        )
        history.append({"role": "user", "content": article})
        if "error" not in result:
            history.append({"role": "assistant", "content": str(result)})
        state_manager.update_history(session_id, history)
        return {"result": result, "session_id": session_id}
    except Exception as e:
        return {"error": "Extraction failed", "details": str(e), "session_id": session_id}

@plugin_api
async def extract_(article: str, model_name: str = None) -> dict:
    """
    插件API：无状态抽取。
    """
    try:
        result = await extract_info(article)
        return {"result": result}
    except Exception as e:
        return {"error": "Stateless extraction failed", "details": str(e)} 