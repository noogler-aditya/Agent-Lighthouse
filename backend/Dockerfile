FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade "pip>=24.3.1" "wheel>=0.46.2" \
    && pip install --no-cache-dir -r requirements.txt \
    && (pip uninstall -y jaraco.context || true)

# Copy source
COPY . .

# Drop root privileges for runtime.
RUN groupadd --system app && useradd --system --gid app app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
