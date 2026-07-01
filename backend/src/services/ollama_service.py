import os
import requests


def get_downloaded_models():
    """Fetches the list of text models downloaded in Ollama, filtering out background embedding models."""
    # 👇 FIXED: Standardized to use the environment parameter variable with correct port assignment
    base_url = os.getenv("OLLAMA_URL", "http://docker.internal")

    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()

        data = response.json()

        model_names = []
        for model in data.get("models", []):
            name = model["name"]
            
            if "embed" in name.lower() or "vector" in name.lower():
                continue
                
            model_names.append(name)
            
        return model_names

    except Exception as e:
        print(f"Error fetching Ollama models: {e}")
        return []
