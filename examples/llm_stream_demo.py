import requests

url = 'http://localhost:8000/llm_invoke?stream=true'
data = {
    'prompt': '你好，介绍一下AICoreDirector的主要功能',
    # 可根据需要添加其他参数，如model_name、temperature等
}

with requests.post(url, json=data, stream=True) as resp:
    print('Status:', resp.status_code)
    print('--- 流式返回内容 ---')
    for chunk in resp.iter_content(chunk_size=None):
        if chunk:
            print(chunk.decode('utf-8'), end='', flush=True)
    print('\n--- 结束 ---') 