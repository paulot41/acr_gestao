#!/bin/bash

# ACR Gestão - Script de Início Rápido
# Deploy automático para Docker Desktop

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}"
echo "==========================================="
echo "🚀 ACR Gestão - Deploy Rápido"
echo "==========================================="
echo -e "${NC}"

echo "Este script irá:"
echo "1. Validar o sistema"
echo "2. Fazer build e deploy automático"
echo "3. Configurar dados iniciais"
echo "4. Mostrar URLs de acesso"
echo

read -p "Continuar? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Deploy cancelado."
    exit 0
fi

echo -e "${BLUE}🔍 Executando validação...${NC}"
if ./validate_setup.sh; then
    echo -e "${GREEN}✅ Validação passou!${NC}"
else
    echo -e "${YELLOW}⚠️  Há alguns avisos, mas continuando...${NC}"
fi

echo
echo -e "${BLUE}🚀 Iniciando deploy automático...${NC}"

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose -f docker-compose.base-nginx.yml down --remove-orphans 2>/dev/null || true

# Build e deploy
echo "🔨 Fazendo build e iniciando containers..."
docker-compose -f docker-compose.base-nginx.yml up -d --build

# Aguardar serviços
echo "⏳ Aguardando serviços ficarem prontos..."
sleep 30

# Verificar se containers estão a correr
if ! docker-compose -f docker-compose.base-nginx.yml ps | grep -q "Up"; then
    echo "❌ Alguns containers não estão a correr!"
    docker-compose -f docker-compose.base-nginx.yml logs
    exit 1
fi

# Migrações
echo "📊 Executando migrações..."
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py migrate

# Ficheiros estáticos
echo "📁 Recolhendo ficheiros estáticos..."
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py collectstatic --noinput

# Criar superuser
echo "👤 Criando superuser..."
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@acr.local', 'admin123')
    print("✅ Superuser 'admin' criado")
else:
    print("ℹ️  Superuser 'admin' já existe")
EOF

# Dados iniciais
echo "🎯 Criando dados iniciais..."
docker-compose -f docker-compose.base-nginx.yml exec web python /app/init_data.py

echo
echo -e "${GREEN}🎉 Deploy completo!${NC}"
echo
echo "🌐 URLs disponíveis:"
echo "  📱 Interface Principal:  http://localhost:8080/"
echo "  🎯 Gantt Dinâmico:      http://localhost:8080/gantt/"
echo "  ⚙️  Admin Django:        http://localhost:8080/admin/"
echo "  📊 Dashboard:           http://localhost:8080/dashboard/"
echo
echo "👤 Credenciais:"
echo "  Username: admin"
echo "  Password: admin123"
echo
echo "📋 Para gestão avançada, use: ./deploy_local.sh"
echo
