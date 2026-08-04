FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UV_HTTP_TIMEOUT=120

# only rebuilds when the manifests change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# edits here reuse the cached deps above
COPY . .

EXPOSE 8000
CMD ["uv", "run", "fastapi", "run", "app/main.py", "--port", "8000"]