import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="PrepMed Frontend Router", version="2.0")

BASE_DIR = Path(__file__).resolve().parent
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


async def get_json(path: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BACKEND_URL}{path}")
        response.raise_for_status()
        return response.json()


def get_model_name(model):
    if isinstance(model, str):
        return model

    return model.get("name") or model.get("model") or str(model)


async def render_page(request: Request, template_name: str, extra: dict | None = None):
    context = {
        "request": request,
        "users": await get_json("/api/users"),
    }

    if extra:
        context.update(extra)

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=context,
    )


@app.get("/", response_class=HTMLResponse)
async def view_consultation_page(request: Request):
    models = await get_json("/models")

    return await render_page(
        request,
        "index.html",
        {
            "templates": await get_json("/api/templates"),
            "sessions": await get_json("/api/sessions"),
            "ollama_models": [
                get_model_name(model)
                for model in models.get("ollama_models", [])
            ],
            "gemini_models": [
                get_model_name(model)
                for model in models.get("gemini_models", [])
            ],
        },
    )


@app.get("/users/new", response_class=HTMLResponse)
async def view_create_user_page(request: Request):
    return await render_page(request, "create_user.html")


@app.get("/templates/new", response_class=HTMLResponse)
async def view_create_template_page(request: Request):
    return await render_page(request, "create_template.html")


@app.get("/history")
async def redirect_history_to_home():
    return RedirectResponse(url="/")


async def proxy_to_backend(request: Request, path: str):
    url = f"{BACKEND_URL}{path}"

    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=await request.body(),
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type", "application/json"),
    )


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_api_routes(path: str, request: Request):
    return await proxy_to_backend(request, f"/api/{path}")


@app.api_route("/models", methods=["GET"])
async def proxy_models_route(request: Request):
    return await proxy_to_backend(request, "/models")