import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="PrepMed B&W Frontend Router", version="2.0")
templates = Jinja2Templates(directory="src/templates")

# Read the URL directly from your frontend/.env file configuration
BACKEND_URL_ENV = os.getenv("BACKEND_URL", "http://localhost:8000")


@app.get("/", response_class=HTMLResponse)
async def view_history_table_page(request: Request):
    """Main historical table list page views."""
    return templates.TemplateResponse(
        request=request, 
        name="history.html",
        context={"request": request, "backend_url": BACKEND_URL_ENV}
    )


@app.get("/record", response_class=HTMLResponse)
async def view_live_recording_page(request: Request):
    """Live microphone session processing template view."""
    return templates.TemplateResponse(
        request=request, 
        name="recording.html",
        context={"request": request, "backend_url": BACKEND_URL_ENV}
    )


@app.get("/detail/{consultation_id}", response_class=HTMLResponse)
async def view_report_detail_page(request: Request, consultation_id: int):
    """Editable human-in-the-loop review parameter view."""
    return templates.TemplateResponse(
        request=request,
        name="detail.html",
        context={
            "request": request, 
            "consultation_id": consultation_id,
            "backend_url": BACKEND_URL_ENV 
        }
    )
