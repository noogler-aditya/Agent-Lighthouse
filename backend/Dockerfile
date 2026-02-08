FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade "pip>=24.3.1" "wheel>=0.46.2" \
    && pip install --no-cache-dir -r requirements.txt \
    && (pip uninstall -y wheel jaraco.context || true) \
    && python - <<'PY'
import shutil
import sysconfig
from pathlib import Path

site = Path(sysconfig.get_paths()["purelib"])
patterns = (
    "wheel",
    "wheel-*.dist-info",
    "jaraco",
    "jaraco.context-*.dist-info",
)
for pattern in patterns:
    for path in site.glob(pattern):
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
PY

# Copy source
COPY . .

# Drop root privileges for runtime.
RUN groupadd --system app && useradd --system --gid app app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
