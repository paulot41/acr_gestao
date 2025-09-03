#!/bin/bash
set -e

echo "=== ACR Gestão - Validação Pré-Deploy ==="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🔍 Verificando pré-requisitos..."

# Verificar Docker
if command -v docker &> /dev/null; then
    success "Docker instalado"
else
    error "Docker não encontrado. Instale o Docker primeiro."
    exit 1
fi

# Verificar Docker Compose
if command -v docker-compose &> /dev/null; then
    success "Docker Compose instalado"
else
    error "Docker Compose não encontrado. Instale o Docker Compose primeiro."
    exit 1
fi

# Verificar arquivo .env.prod
if [ -f ".env.prod" ]; then
    success "Arquivo .env.prod encontrado"

    # Verificar SECRET_KEY
    if grep -q "your_super_secret_key_here" .env.prod; then
        error "SECRET_KEY ainda não foi configurada no .env.prod!"
        echo "   Execute: python -c 'import secrets; print(secrets.token_urlsafe(50))'"
        exit 1
    else
        success "SECRET_KEY configurada"
    fi

    # Verificar DEBUG
    if grep -q "DEBUG=0" .env.prod; then
        success "DEBUG=0 configurado para produção"
    else
        warning "DEBUG deveria ser 0 em produção"
    fi

    # Verificar ALLOWED_HOSTS
    if grep -q "ALLOWED_HOSTS=" .env.prod; then
        success "ALLOWED_HOSTS configurado"
    else
        error "ALLOWED_HOSTS não configurado"
        exit 1
    fi
else
    error "Arquivo .env.prod não encontrado!"
    echo "   Execute: cp .env.prod.example .env.prod"
    echo "   Depois edite o arquivo com suas configurações"
    exit 1
fi

echo ""
echo "🧪 Testando configuração Django..."

# Verificar migrações
python manage.py check --deploy > /dev/null 2>&1
if [ $? -eq 0 ]; then
    success "Configurações Django válidas"
else
    error "Problemas encontrados nas configurações Django"
    python manage.py check --deploy
    exit 1
fi

# Verificar se há migrações pendentes
PENDING=$(python manage.py showmigrations --plan | grep '\[ \]' | wc -l)
if [ $PENDING -eq 0 ]; then
    success "Todas as migrações aplicadas"
else
    warning "$PENDING migrações pendentes. Execute: python manage.py migrate"
fi

echo ""
echo "📁 Verificando estrutura de arquivos..."

# Verificar arquivos essenciais
REQUIRED_FILES=(
    "Dockerfile"
    "docker-compose.yml"
    "docker-compose.prod.yml"
    "Caddyfile"
    "requirements.txt"
    "manage.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "$file presente"
    else
        error "$file não encontrado"
        exit 1
    fi
done

# Verificar diretórios
REQUIRED_DIRS=(
    "backups"
    "logs"
    "staticfiles"
    "core"
    "acr_gestao"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        success "Diretório $dir presente"
    else
        warning "Diretório $dir não encontrado (será criado automaticamente)"
    fi
done

echo ""
echo "🐳 Testando build do Docker..."

# Test Docker build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build web --quiet
if [ $? -eq 0 ]; then
    success "Build do container Django bem-sucedido"
else
    error "Falha no build do container Django"
    exit 1
fi

echo ""
echo "${GREEN}🎉 Sistema pronto para deploy!${NC}"
echo ""
echo "📋 Próximos passos:"
echo "   1. Execute: ./deploy.sh"
echo "   2. Configure superusuário e organizações"
echo "   3. Teste o acesso via browser"
echo "   4. Configure monitoramento: ./monitor.sh"
echo ""
echo "🔗 URLs do sistema:"
echo "   - https://acrsantatecla.duckdns.org"
echo "   - https://proformsc.duckdns.org"
