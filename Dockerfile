FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# garantir diretórios estáticos/media
RUN python -c "import pathlib; pathlib.Path('staticfiles').mkdir(exist_ok=True); pathlib.Path('media').mkdir(exist_ok=True)" \
 && (python manage.py collectstatic --noinput || true)

EXPOSE 8000
CMD ["gunicorn","acr_gestao.wsgi:application","--bind","0.0.0.0:8000"]
