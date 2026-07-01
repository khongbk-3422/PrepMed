# 🩺 PrepMed: Local Audio Clinical Data Extractor Framework

An offline-first medical audio transcription and structured report pipeline. This system converts live spoken clinical dictations directly into standardized medical schemas inside the browser, passing payloads to a local AI model for structural mapping into template questionnaires.

---

## 🏗️ Architecture Design Matrix

- **Frontend Container (`FastAPI + Jinja2 + Web Speech API`)**: A minimalist, low-latency, black-and-white dashboard. It records live audio, streams live text dictations, handles pause/resume logic, and manages session audits.
- **Backend API Container (`FastAPI + SQLModel`)**: Runs text extraction transformations, routes dynamic engine selections, and outputs data through custom serializers to bypass type locks.
- **PostgreSQL Database (`pgvector`)**: Stores system users, medical templates, and processed consultation summaries securely.
- **Local AI Engine (`Ollama`)**: Completely offline model runtime utilizing your machine's graphics card processor.

---

## ⚡ Quick Start Deployment

### Prerequisites
1. Install [Docker Desktop](https://docker.com).
2. Install [Ollama](https://ollama.com) locally on your laptop host.
3. Download required operational weight models via your laptop command terminal:
   ```powershell
   ollama pull llama3.1
   ollama pull nomic-embed-text
   ```

### 1. Unlock Local Ollama Gateway Network (Windows)
1. Close Ollama completely from your Windows system tray icon (bottom right).
2. Open **PowerShell** and run these commands to set the binding variable and restart the server:
   ```powershell
   [System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0', 'User')
   ollama serve
   ```

### 2. Launch the Application Container Stack
Navigate to your main root project directory (`prepmed-project/`) and run:
```powershell
# Build and lift all network containers in background mode
docker compose up --build -d

# Seed required default system users and questionnaire templates into PostgreSQL
docker compose exec backend /app/.venv/bin/python src/seed.py
```

### 3. Open Endpoints
- **Frontend Workspace Dashboard**: `http://localhost:3000`
- **Interactive Backend API Documentation**: `http://localhost:8000/docs`

---

## 🛠️ Internal Project Components Management

### Linting and Code Formatting
Both repositories utilize `ruff` for code cleanliness constraints. Run formatting audits directly inside subfolders:
```powershell
uv run ruff check .
```
