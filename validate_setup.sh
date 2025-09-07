#!/bin/bash

# ACR Gestão - Script de Validação Pre-Deploy
# Versão: 1.0

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo -e "${BLUE}"
echo "==========================================="
echo "🔍 ACR Gestão - Validação Pre-Deploy"
echo "==========================================="
echo -e "${NC}"

errors=0

# 1. Verificar Docker
print_info "Verificando Docker..."
if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        print_success "Docker está instalado e a correr"
    else
        print_error "Docker está instalado mas não está a correr"
        print_info "Inicie o Docker Desktop e tente novamente"
        ((errors++))
    fi
else
    print_error "Docker não está instalado"
    print_info "Instale o Docker Desktop primeiro"
    ((errors++))
fi

# 2. Verificar docker-compose
print_info "Verificando docker-compose..."
if command -v docker-compose >/dev/null 2>&1; then
    print_success "docker-compose está disponível"
else
    print_error "docker-compose não está instalado"
    ((errors++))
fi

# 3. Verificar ficheiros necessários
print_info "Verificando ficheiros necessários..."

required_files=(
    "docker-compose.base-nginx.yml"
    ".env.local"
    "nginx.conf"
    "Dockerfile"
    "requirements.txt"
    "manage.py"
    "init_data.py"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        print_success "Ficheiro encontrado: $file"
    else
        print_error "Ficheiro em falta: $file"
        ((errors++))
    fi
done

# 4. Verificar estrutura de diretórios
print_info "Verificando estrutura de diretórios..."

required_dirs=(
    "core"
    "acr_gestao"
    "static"
    "media"
)

for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        print_success "Diretório encontrado: $dir"
    else
        print_error "Diretório em falta: $dir"
        ((errors++))
    fi
done

# 5. Verificar porta 80 disponível
print_info "Verificando disponibilidade da porta 80..."
if command -v lsof >/dev/null 2>&1; then
    if lsof -i :80 >/dev/null 2>&1; then
        print_warning "Porta 80 está ocupada"
        print_info "Pode ser necessário parar outros serviços web"
        print_info "Ou alterar a porta no docker-compose.base-nginx.yml"
    else
        print_success "Porta 80 está disponível"
    fi
else
    print_warning "Comando 'lsof' não disponível, não foi possível verificar a porta 80"
fi

# 6. Verificar configuração do ambiente
print_info "Verificando configuração do ambiente..."
if [[ -f ".env.local" ]]; then
    if grep -q "SECRET_KEY=" .env.local && grep -q "DB_NAME=" .env.local; then
        print_success "Configuração do ambiente parece válida"
    else
        print_warning "Configuração do ambiente pode estar incompleta"
        print_info "Verifique se .env.local tem todas as variáveis necessárias"
    fi
fi

# 7. Verificar permissions nos scripts
print_info "Verificando permissões dos scripts..."
if [[ -x "deploy_local.sh" ]]; then
    print_success "Script deploy_local.sh é executável"
else
    print_warning "Script deploy_local.sh não é executável"
    print_info "Execute: chmod +x deploy_local.sh"
fi

# Resumo final
echo
echo "==========================================="
if [[ $errors -eq 0 ]]; then
    print_success "🎉 Todos os testes passaram! Sistema pronto para deploy."
    echo
    print_info "Para fazer deploy, execute:"
    echo "  ./deploy_local.sh"
else
    print_error "❌ Encontrados $errors erro(s). Corrija antes de continuar."
    echo
    print_info "Após corrigir os erros, execute novamente este script."
fi
echo "==========================================="
echo
