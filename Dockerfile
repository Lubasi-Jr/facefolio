# ---- builder ----
# Install dependencies into a virtual environment using uv.
# Using the same base image in both stages guarantees the Python interpreter
# version is identical, so the copied .venv is bit-for-bit compatible.
FROM python:3.14-slim AS builder

# Grab just the uv binary from the official image — no extra layer baggage.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy manifests first so Docker cache busts only when deps change, not on code edits.
COPY pyproject.toml uv.lock ./

# --frozen     : fail if uv.lock is out of sync with pyproject.toml (keeps builds reproducible)
# --no-install-project : install deps only, not the project itself (it's an app, not a library)
# --no-cache   : skip uv's download cache (no persistent cache mount here, so it just wastes space)
RUN uv sync --frozen --no-install-project --no-cache


# ---- final ----
FROM python:3.14-slim AS final

WORKDIR /app

# Copy the populated virtual environment; everything else from the builder is discarded.
COPY --from=builder /app/.venv /app/.venv

# Copy application source.
COPY app/ ./app/

# Activate the venv by prepending its bin dir to PATH.
ENV PATH="/app/.venv/bin:$PATH" \
    # Don't write .pyc files into the image.
    PYTHONDONTWRITEBYTECODE=1 \
    # Keep stdout/stderr unbuffered so uvicorn logs appear immediately in `docker logs`.
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
