import os
import json
import requests
from sqlmodel import Session
from google import genai
from google.genai import types

# Setup system environment targets dynamically
OLLAMA_HOST = os.getenv("OLLAMA_URL", "http://localhost:11434") # Usually ends in /api/generate if using raw requests

def process_clinical_audio(db: Session, raw_text: str, required_keys: list[str], d_desc: str, d_med: str, model_name: str = "llama3.1") -> dict:
    """Extracts unstructured conversation data directly using official Google GenAI SDK or Local Ollama."""
    
    # Pre-build our explicit fallback dictionary structure matrix
    fallback_dict = {key: "-" for key in required_keys}
    fallback_dict.update({"description": d_desc, "medicine": d_med})

    # Pass clean schemas to the AI without embedding the fallback strings as default template values
    schema_blueprint = {key: "Extract value from transcript, fallback to '-' if missing" for key in required_keys}
    schema_blueprint["description"] = "A cohesive paragraph synthesizing the clinical summary analysis of the raw consultation transcript."
    schema_blueprint["medicine"] = "Explicit list of prescribed drugs along with their associated structural dosages."

    system_prompt = f"""
    You are an advanced medical clinical data extractor. Your job is to analyze the audio transcript and fill in the required fields.
    If information for a field is missing or not mentioned, you MUST set its value to "-".
    
    You MUST output raw JSON matching this layout exactly. Do not include any markdown boxes, extra conversational text, or backticks:
    {json.dumps(schema_blueprint)}
    """

    full_prompt = f"{system_prompt}\nTarget Audio Transcript: {raw_text}"
    raw_json_str = ""

    # 👇 PATH 1: ROUTE TO CLOUD GOOGLE GEMINI via Official SDK
    if model_name.strip().lower().startswith("gemini"):
        print(f"☁️ Cloud Inference Active: Routing via google-genai SDK ({model_name})")
        client = genai.Client()
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        raw_json_str = response.text

    # 👇 PATH 2: ROUTE TO LOCAL OLLAMA MODULE RUNTIME
    elif model_name.strip().lower().startswith("ollama-"):
        actual_model = model_name.replace("ollama-", "", 1)
        print(f"💻 Local GPU Inference Active: Routing payload straight to Ollama ({actual_model})")
        
        # Ensure url points to the generation endpoint
        url = OLLAMA_HOST if OLLAMA_HOST.endswith("/api/generate") else f"{OLLAMA_HOST}/api/generate"
        
        payload = {
            "model": actual_model,
            "prompt": full_prompt,
            "format": "json",  # Forces Ollama to output valid JSON
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=45)
            if response.status_code == 200:
                raw_json_str = response.json().get("response", "")
            else:
                print(f"⚠️ Ollama Service returned Warning Code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"⚠️ Local Ollama Network Transaction Failed: {e}")
            
    else:
        print("⚠️ Error: Unknown model routing.")

    # ⭐ Parse output string and apply CRITICAL SAFETY NET
    if raw_json_str:
        try:
            return json.loads(raw_json_str)
        except Exception as json_err:
            print(f"⚠️ Failed to parse AI response as JSON: {json_err}\nRaw Response: {raw_json_str}")

    return fallback_dict