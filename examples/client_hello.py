import requests

def call_hello_plugin(name="World"):
    url = "http://127.0.0.1:8000/hello"
    payload = {"name": name}
    response = requests.post(url, json=payload)
    print("Status:", response.status_code)
    print("Raw Response:", response.text)
    try:
        print("JSON Response:", response.json())
    except Exception as e:
        print("JSON decode error:", e)

if __name__ == "__main__":
    call_hello_plugin("Alice") 