FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências de build (psycopg etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Instalar requirements primeiro (melhor cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Garantir diretório de estáticos existe (evita warnings)
RUN mkdir -p /app/staticfiles

# Tenta collectstatic mas não falha o build se não estiver configurado ainda
RUN python -c "import pathlib; pathlib.Path('staticfiles').mkdir(exist_ok=True)" \
 && (python manage.py collectstatic --noinput || true)

# Gunicorn em 0.0.0.0:8000
CMD ["gunicorn", "acr_gestao.wsgi:application", "--bind", "0.0.0.0:8000"]
