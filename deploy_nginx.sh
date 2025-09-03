#!/bin/bash
set -e

echo "=== ACR Gestão - Deploy com Nginx ==="

# Verificar se arquivo .env.prod existe
if [ ! -f ".env.prod" ]; then
    echo "❌ Arquivo .env.prod não encontrado!"
    echo "📋 Copie .env.prod.example para .env.prod e configure as variáveis:"
    echo "   cp .env.prod.example .env.prod"
    exit 1
fi

echo "✅ Arquivo .env.prod encontrado"

# Verificar se SECRET_KEY está configurada
if grep -q "your_super_secret_key_here" .env.prod; then
    echo "❌ SECRET_KEY ainda não foi configurada no .env.prod!"
    echo "🔑 Gere uma chave segura com:"
    echo "   python -c 'import secrets; print(secrets.token_urlsafe(50))'"
    exit 1
fi

echo "✅ SECRET_KEY configurada"

# Preparar SSL se necessário
if [ ! -f "ssl/nginx-selfsigned.crt" ]; then
    echo "🔐 Configurando SSL..."
    ./setup_ssl.sh
fi

echo "✅ Certificados SSL preparados"

# Build e deploy
echo "🔨 Construindo containers..."
docker-compose -f docker-compose.yml -f docker-compose.nginx.yml build

echo "🗄️ Iniciando base de dados..."
docker-compose -f docker-compose.yml -f docker-compose.nginx.yml up -d db

echo "⏳ Aguardando base de dados..."
sleep 10

echo "🔄 Executando migrações..."
docker-compose -f docker-compose.yml -f docker-compose.nginx.yml run --rm web python manage.py migrate

echo "📦 Coletando arquivos estáticos..."
docker-compose -f docker-compose.yml -f docker-compose.nginx.yml run --rm web python manage.py collectstatic --noinput

echo "🚀 Iniciando todos os serviços..."
docker-compose -f docker-compose.yml -f docker-compose.nginx.yml up -d

echo "🔍 Verificando estado dos serviços..."
docker-compose -f docker-compose.yml -f docker-compose.nginx.yml ps

echo "✅ Deploy com Nginx concluído!"
echo "🌐 O sistema deve estar disponível em:"
echo "   - https://acrsantatecla.duckdns.org"
echo "   - https://proformsc.duckdns.org"
echo "   - http://localhost (para testes locais)"
echo ""
echo "🔐 Para certificados SSL de produção:"
echo "   ./setup_ssl.sh production"
echo ""
echo "📊 Para monitorar os logs:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.nginx.yml logs -f"
