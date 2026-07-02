import os
import requests


def get_downloaded_models():
    """Fetches the list of text models downloaded in Ollama, allowing sufficient buffer for GPU initialization."""
    base_url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    base_url = base_url.rstrip("/")

    try:
        # 👇 FIXED: Increased timeout buffer threshold from 5 to 15 seconds!
        response = requests.get(f"{base_url}/api/tags", timeout=15)
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
