import os


def get_gemini_models():
    models = []

    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "rate_limits.txt")

    try:
        with open(file_path, "r") as file:
            content = file.read()
            # Split the entire file by any whitespace (spaces, tabs, newlines)
            words = content.split()

            # Loop through every single word and grab the ones starting with gemini
            for word in words:
                if word.strip().startswith("gemini"):
                    models.append(word.strip())

        print(f"DEBUG: Successfully extracted all models: {models}")
    except Exception as e:
        print(f"DEBUG: Failed to read file. Error: {e}")
        models = ["gemini-3-flash-preview"]  # Fallback

    return models
