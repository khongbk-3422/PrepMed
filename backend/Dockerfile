FROM python:3.14-bookworm 

# Install uv directly from astral-sh into your binary path
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory inside the container
WORKDIR /app

# Copy the lockfile and pyproject.toml first for layer caching
COPY pyproject.toml uv.lock ./

# Install the dependencies cleanly using uv without dev dependencies
RUN uv sync --frozen --no-dev

# Copy the rest of the source code matching your folder layout
COPY src ./src

# Expose your FastAPI port
EXPOSE 8000

# Run uvicorn directly through uv using the correct src path namespace
ENTRYPOINT ["uv", "run", "uvicorn"]
CMD ["src.main:app", "--host", "0.0.0.0", "--port", "8000"]