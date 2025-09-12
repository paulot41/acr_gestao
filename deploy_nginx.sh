#!/bin/bash
# Deploy de Nginx com certificados Let's Encrypt
set -e

DOMAIN=${DOMAIN:?"Defina o domínio em DOMAIN"}
EMAIL=${EMAIL:?"Defina o email de contacto em EMAIL"}

mkdir -p certbot/conf certbot/www

if [ ! -d "certbot/conf/live/$DOMAIN" ]; then
  echo "📜 A obter certificado para $DOMAIN..."
  docker run --rm -p 80:80 \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    certbot/certbot certonly --standalone \
    --non-interactive --agree-tos --email "$EMAIL" -d "$DOMAIN"
fi

echo "🚀 A iniciar Nginx com SSL..."
docker rm -f nginx 2>/dev/null || true

docker run -d --name nginx \
  -p 80:80 -p 443:443 \
  -v "$(pwd)/nginx-prod.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt:ro" \
  -v "$(pwd)/staticfiles:/app/staticfiles:ro" \
  -v "$(pwd)/media:/app/media:ro" \
  nginx:alpine

echo "✅ Nginx pronto com certificados Let's Encrypt"
