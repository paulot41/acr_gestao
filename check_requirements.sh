#!/bin/bash

echo "=== Verificação de Requisitos - ACR Gestão ==="
echo "Data: $(date)"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

echo "🔍 Verificando versões dos componentes..."
echo ""

# Verificar sistema operacional
echo "📋 Sistema Operacional:"
if [ -f /etc/os-release ]; then
    source /etc/os-release
    success "OS: $PRETTY_NAME"
else
    info "OS: $(uname -s) $(uname -r)"
fi
echo ""

# Verificar Docker
echo "🐳 Docker:"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    success "$DOCKER_VERSION"

    # Verificar se Docker está rodando
    if docker ps &> /dev/null; then
        success "Docker daemon está rodando"
    else
        error "Docker daemon não está rodando"
        echo "   Execute: sudo systemctl start docker"
    fi

    # Verificar permissões do usuário
    if groups | grep -q docker; then
        success "Usuário $(whoami) está no grupo docker"
    else
        warning "Usuário $(whoami) não está no grupo docker"
        echo "   Execute: sudo usermod -aG docker $(whoami) && newgrp docker"
    fi
else
    error "Docker não encontrado"
fi
echo ""

# Verificar Docker Compose
echo "🔧 Docker Compose:"
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    success "$COMPOSE_VERSION"
elif docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version)
    success "$COMPOSE_VERSION (plugin)"
else
    error "Docker Compose não encontrado"
fi
echo ""

# Verificar Git
echo "📁 Git:"
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    success "$GIT_VERSION"
else
    error "Git não encontrado"
fi
echo ""

# Verificar Python3
echo "🐍 Python:"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    success "$PYTHON_VERSION"
else
    warning "Python3 não encontrado (necessário apenas para gerar SECRET_KEY)"
fi
echo ""

# Verificar curl
echo "🌐 Curl:"
if command -v curl &> /dev/null; then
    CURL_VERSION=$(curl --version | head -n1)
    success "$CURL_VERSION"
else
    warning "Curl não encontrado (útil para testes)"
fi
echo ""

# Verificar portas
echo "🔌 Verificação de Portas:"
check_port() {
    local port=$1
    local service=$2

    if ss -tuln | grep -q ":$port "; then
        warning "Porta $port está em uso ($service)"
        echo "   Processo usando a porta:"
        ss -tulnp | grep ":$port "
    else
        success "Porta $port está livre ($service)"
    fi
}

check_port 80 "HTTP"
check_port 443 "HTTPS"
check_port 5432 "PostgreSQL"
check_port 8000 "Django"
echo ""

# Verificar espaço em disco
echo "💾 Espaço em Disco:"
df -h / | tail -n1 | while read filesystem size used avail percent mountpoint; do
    if [[ ${percent%?} -lt 80 ]]; then
        success "Espaço disponível: $avail ($percent usado)"
    else
        warning "Pouco espaço disponível: $avail ($percent usado)"
    fi
done
echo ""

# Verificar memória
echo "🧠 Memória:"
total_mem=$(free -h | awk '/^Mem:/ {print $2}')
avail_mem=$(free -h | awk '/^Mem:/ {print $7}')
success "Memória total: $total_mem (disponível: $avail_mem)"
echo ""

# Verificar conectividade
echo "🌐 Conectividade:"
if ping -c 1 google.com &> /dev/null; then
    success "Conectividade com internet OK"
else
    error "Sem conectividade com internet"
fi

if ping -c 1 github.com &> /dev/null; then
    success "Conectividade com GitHub OK"
else
    error "Sem conectividade com GitHub"
fi
echo ""

# Resumo
echo "📊 Resumo:"
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null && command -v git &> /dev/null; then
    success "Todos os requisitos principais estão instalados!"
    echo ""
    info "Próximos passos:"
    echo "   1. cd acr_gestao"
    echo "   2. git pull origin main"
    echo "   3. ./validate.sh"
    echo "   4. ./deploy.sh"
else
    error "Alguns requisitos estão em falta. Instale-os antes de continuar."
fi
