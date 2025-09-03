#!/bin/bash
set -e

echo "=== ACR Gestão - Script de Deploy para Produção ==="

# Verificar se arquivo .env.prod existe
if [ ! -f ".env.prod" ]; then
    echo "❌ Arquivo .env.prod não encontrado!"
    echo "📋 Copie .env.prod.example para .env.prod e configure as variáveis:"
    echo "   cp .env.prod.example .env.prod"
    echo "   # Edite .env.prod com suas configurações"
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

# Preparar diretórios com permissões corretas
echo "📁 Preparando diretórios..."
mkdir -p staticfiles media logs backups

# Obter UID do usuário appuser do container (1001)
APPUSER_UID=1001
APPUSER_GID=1001

# Ajustar permissões para o usuário do container
sudo chown -R $APPUSER_UID:$APPUSER_GID staticfiles/ media/ logs/
sudo chown -R $(id -u):$(id -g) backups/
echo "✅ Permissões ajustadas"

# Build e deploy
echo "🔨 Construindo containers..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

echo "🗄️ Iniciando base de dados..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d db

echo "⏳ Aguardando base de dados..."
sleep 10

echo "🔄 Executando migrações..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm web python manage.py migrate

echo "📦 Coletando arquivos estáticos..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput

echo "🚀 Iniciando todos os serviços..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo "🔍 Verificando estado dos serviços..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

echo "✅ Deploy concluído!"
echo "🌐 O sistema deve estar disponível em:"
echo "   - https://acrsantatecla.duckdns.org"
echo "   - https://proformsc.duckdns.org"
echo ""
echo "📊 Para monitorar os logs:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f"
