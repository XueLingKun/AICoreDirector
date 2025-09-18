import requests
import json

# The base URL of your running FastAPI application
BASE_URL = "http://127.0.0.1:8000"

def print_response(message, response):
    """Helper function to pretty-print the server's response."""
    print(f"--- {message} ---")
    try:
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print("Response Text:")
        print(response.text)
    print("-" * (len(message) + 8))
    print()


def manage_llm(action, model_name, base_url=None, api_key=None):
    """A wrapper function to call the /manage_LLM endpoint."""
    payload = {
        "action": action,
        "model_name": model_name,
        "base_url": base_url,
        "api_key": api_key
    }
    # Filter out None values so they are not sent in the payload
    payload = {k: v for k, v in payload.items() if v is not None}
    response = requests.post(f"{BASE_URL}/manage_LLM", json=payload)
    return response

def invoke_llm(prompt, model_name=None):
    """A wrapper function to call the /llm_invoke endpoint."""
    payload = {"prompt": prompt, "model_name": model_name}
    response = requests.post(f"{BASE_URL}/llm_invoke", json=payload)
    return response

def list_llms():
    """A wrapper function to call the /list_models endpoint."""
    response = requests.post(f"{BASE_URL}/list_models")
    return response

def run_demo():
    """Runs a sequence of operations to demonstrate the API."""
    
    # 1. List initial models
    resp = list_llms()
    print_response("Initial Model List", resp)

    # 2. Add a new model
    new_model_name = "my-test-model"
    new_model_url = "http://localhost:11434/v1"
    new_model_key = "ollama" # Example key, use a real one if needed
    resp = manage_llm('add', new_model_name, new_model_url, new_model_key)
    print_response(f"Adding Model: {new_model_name}", resp)

    # 3. List models again to see the new addition
    resp = list_llms()
    print_response("Model List After Add", resp)

    # 4. Invoke the newly added model specifically
    prompt = "Who are you and what can you do?"
    resp = invoke_llm(prompt, model_name=new_model_name)
    print_response(f"Invoking Specific Model: {new_model_name}", resp)

    # 5. Invoke a model without specifying a name (uses the pool's default logic)
    resp = invoke_llm(prompt)
    print_response("Invoking Default Model from Pool", resp)

    # 6. Update the model's details
    updated_model_url = "http://localhost:11435/v1" # Changed port
    updated_model_key = "ollama_new_key"
    resp = manage_llm('update', new_model_name, updated_model_url, updated_model_key)
    print_response(f"Updating Model: {new_model_name}", resp)

    # 7. List models to verify the update (note: update doesn't change the name)
    resp = list_llms()
    print_response("Model List After Update", resp)

    # 8. Delete the model
    resp = manage_llm('delete', new_model_name)
    print_response(f"Deleting Model: {new_model_name}", resp)

    # 9. Final list of models
    resp = list_llms()
    print_response("Final Model List", resp)


if __name__ == "__main__":
    #run_demo()
    prompt = "中国的首都?"
    resp = invoke_llm(prompt)
    print_response(f"Invoking Specific Model: ", resp) 