import os
import json
import requests
from sqlmodel import Session
import google.generativeai as genai

# Setup system environment targets dynamically
OLLAMA_HOST = os.getenv("OLLAMA_URL", "http://docker.internal")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
genai.configure(api_key=GEMINI_KEY)


def process_clinical_audio(db: Session, raw_text: str, required_keys: list[str], d_desc: str, d_med: str, model_name: str = "llama3.1") -> dict:
    """Extracts unstructured conversation data directly using your chosen Local Ollama or Cloud Gemini architecture."""
    
    schema_blueprint = {key: "Extract value from transcript, fallback to '-' if missing" for key in required_keys}
    schema_blueprint["description"] = f"Clinical summary analysis. Fallback template baseline value: {d_desc}"
    schema_blueprint["medicine"] = f"Prescribed drug dosages. Fallback template baseline value: {d_med}"

    system_prompt = f"""
    You are an advanced medical clinical data extractor. Your job is to analyze the audio transcript and fill in the required fields.
    If information for a field is missing or not mentioned, you MUST set its value to "-".
    
    You MUST output raw JSON matching this layout exactly. Do not include any markdown boxes, extra conversational text, or backticks:
    {json.dumps(schema_blueprint)}
    """

    # 👇 OPTION A: ROUTE DIRECT TO CLOUD GOOGLE GEMINI MODELS PIPELINE
    if model_name.strip().lower().startswith("gemini"):
        print(f"☁️ Cloud Inference Active: Routing payload straight to Google Gemini ({model_name})")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                f"{system_prompt}\nTarget Audio Transcript: {raw_text}",
                generation_config={"response_mime_type": "application/json"},
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"⚠️ Gemini API Processing Exception caught: {e}")
            
    # 👇 OPTION B: FALLBACK / ROUTE DIRECT TO LOCAL OLLAMA GPU MODULE RUNTIME
    else:
        print(f"💻 Local GPU Inference Active: Routing payload straight to Ollama ({model_name})")
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {
            "model": model_name,
            "prompt": f"{system_prompt}\nTarget Audio Transcript: {raw_text}",
            "format": "json",
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return json.loads(response.json()["response"])
            else:
                print(f"⚠️ Ollama Service returned Warning Code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"⚠️ Local Ollama Network Transaction Failed: {e}")
        
    # Emergency Processing error layout matrix recovery boundary
    fallback = {key: "-" for key in required_keys}
    fallback.update({"description": d_desc, "medicine": d_med})
    return fallback
