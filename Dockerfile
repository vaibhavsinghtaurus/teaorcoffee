FROM python:3.13-slim

WORKDIR /app

# Install build tools needed by some dependencies
RUN pip install --no-cache-dir poetry==2.1.1

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock README.md ./

# Install dependencies (no dev deps, no virtualenv — we're in a container)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# Copy application source
COPY src/ ./src/

# Ensure the data directory exists for SQLite
RUN mkdir -p data

# Expose the API port
EXPOSE 8000

# Mount point for persistent SQLite database
VOLUME ["/app/data"]

CMD ["uvicorn", "src.teaorcoffee.main:app", "--host", "0.0.0.0", "--port", "8000"]
