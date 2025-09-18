from core.plugin_loader import plugin_api

@plugin_api
def hello(name: str = "World", session_id: str = None, state_manager=None) -> dict:
    """
    插件样例：返回问候语，并展示当前会话历史条数。
    """
    if session_id and state_manager:
        history = state_manager.get_history(session_id)
        history_len = len(history)
    else:
        history_len = 0
    return {
        "message": f"Hello, {name}! This is from the plugin.",
        "session_id": session_id,
        "history_length": history_len
    }

# 未加 @plugin_api 的函数不会被注册为插件API

def hello_2():
    return {"msg": "不会被注册为插件API"} 