FROM python:3.14-bookworm 

# FIXED: Standardized direct binary target path to copy uv cleanly into the system path namespace
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set the working directory inside the container
WORKDIR /app

# Copy the lockfile and pyproject.toml first for layer caching
COPY pyproject.toml uv.lock ./

# Install the dependencies cleanly using uv without dev dependencies
RUN uv sync --frozen --no-dev

# FIXED: Copies your complete directory layout tree (to ensure src/templates/ is included!)
COPY . .

# Expose your Frontend web app port
EXPOSE 3000

# Run uvicorn directly through uv using the correct src path namespace
ENTRYPOINT ["uv", "run", "uvicorn"]
CMD ["src.main:app", "--host", "0.0.0.0", "--port", "3000"]
