# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências de build (psycopg e afins)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Instalar requirements primeiro (melhor cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Evitar falha caso STATIC_ROOT não esteja definido (smoke test)
RUN python - <<'PY'\nimport pathlib; pathlib.Path('staticfiles').mkdir(exist_ok=True)\nPY
RUN python manage.py collectstatic --noinput || true

# Gunicorn em 0.0.0.0:8000
CMD ["gunicorn", "acr_gestao.wsgi:application", "--bind", "0.0.0.0:8000"]
"-b"]