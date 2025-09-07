#!/bin/bash

# ACR Gestão - Script de Deploy Local Docker Desktop
# Versão: 2.0
# Data: 6 Setembro 2025

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variáveis
COMPOSE_FILE="docker-compose.base-nginx.yml"
ENV_FILE=".env.local"
PROJECT_NAME="acr_gestao"

# Funções de utilidade
print_header() {
    echo -e "${BLUE}"
    echo "==========================================="
    echo "🚀 ACR Gestão - Deploy Local Manager"
    echo "==========================================="
    echo -e "${NC}"
}

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

# Verificar se Docker está a correr
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker não está a correr ou não está instalado"
        print_info "Por favor, inicie o Docker Desktop e tente novamente"
        exit 1
    fi
    print_success "Docker está a correr"
}

# Verificar se docker-compose está disponível
check_docker_compose() {
    if ! command -v docker-compose >/dev/null 2>&1; then
        print_error "docker-compose não está instalado"
        exit 1
    fi
    print_success "docker-compose encontrado"
}

# Verificar ficheiros necessários
check_files() {
    local missing_files=()

    if [[ ! -f "$COMPOSE_FILE" ]]; then
        missing_files+=("$COMPOSE_FILE")
    fi

    if [[ ! -f "$ENV_FILE" ]]; then
        missing_files+=("$ENV_FILE")
    fi

    if [[ ! -f "nginx.conf" ]]; then
        missing_files+=("nginx.conf")
    fi

    if [[ ! -f "Dockerfile" ]]; then
        missing_files+=("Dockerfile")
    fi

    if [[ ${#missing_files[@]} -gt 0 ]]; then
        print_error "Ficheiros em falta:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        exit 1
    fi

    print_success "Todos os ficheiros necessários estão presentes"
}

# Parar containers existentes
stop_containers() {
    print_info "A parar containers existentes..."
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true
    print_success "Containers parados"
}

# Limpar volumes (opcional)
clean_volumes() {
    print_warning "Esta operação irá apagar TODOS os dados da base de dados local!"
    read -p "Tem a certeza? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        print_info "A limpar volumes..."
        docker-compose -f "$COMPOSE_FILE" down -v
        docker volume prune -f
        print_success "Volumes limpos"
    else
        print_info "Operação cancelada"
    fi
}

# Build das imagens
build_images() {
    print_info "A fazer build das imagens Docker..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    print_success "Build completo"
}

# Deploy inicial completo
deploy_initial() {
    print_info "🚀 A iniciar deploy inicial completo..."

    stop_containers
    build_images

    print_info "A iniciar containers..."
    docker-compose -f "$COMPOSE_FILE" up -d

    print_info "A aguardar que os serviços fiquem prontos..."
    sleep 30

    # Verificar se os containers estão a correr
    if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        print_error "Alguns containers não estão a correr"
        show_logs
        exit 1
    fi

    print_info "A executar migrações..."
    docker-compose -f "$COMPOSE_FILE" exec web python manage.py migrate

    print_info "A recolher ficheiros estáticos..."
    docker-compose -f "$COMPOSE_FILE" exec web python manage.py collectstatic --noinput

    print_info "A criar superuser..."
    docker-compose -f "$COMPOSE_FILE" exec web python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@acr.local', 'admin123')
    print("✅ Superuser 'admin' criado")
else:
    print("ℹ️  Superuser 'admin' já existe")
EOF

    print_info "A executar script de dados iniciais..."
    docker-compose -f "$COMPOSE_FILE" exec web python /app/init_data.py

    print_success "Deploy inicial completo!"
    show_urls
}

# Deploy rápido (sem rebuild)
deploy_quick() {
    print_info "⚡ A fazer deploy rápido..."

    stop_containers

    print_info "A iniciar containers..."
    docker-compose -f "$COMPOSE_FILE" up -d

    print_info "A aguardar que os serviços fiquem prontos..."
    sleep 20

    print_success "Deploy rápido completo!"
    show_urls
}

# Restart apenas o Django
restart_web() {
    print_info "🔄 A reiniciar apenas o container Django..."
    docker-compose -f "$COMPOSE_FILE" restart web
    print_success "Container Django reiniciado"
}

# Mostrar logs
show_logs() {
    print_info "📋 A mostrar logs dos containers..."
    docker-compose -f "$COMPOSE_FILE" logs --tail=50
}

# Seguir logs em tempo real
follow_logs() {
    print_info "📋 A seguir logs em tempo real (Ctrl+C para sair)..."
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# Status dos containers
show_status() {
    print_info "📊 Status dos containers:"
    docker-compose -f "$COMPOSE_FILE" ps

    print_info "📊 Uso de recursos:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Shell Django
django_shell() {
    print_info "🐍 A abrir shell Django..."
    docker-compose -f "$COMPOSE_FILE" exec web python manage.py shell
}

# Backup da base de dados
backup_db() {
    local backup_file="backups/backup_$(date +%Y%m%d_%H%M%S).sql"
    mkdir -p backups

    print_info "💾 A criar backup da base de dados..."
    docker-compose -f "$COMPOSE_FILE" exec db pg_dump -U acruser -d acrdb_local > "$backup_file"
    print_success "Backup criado: $backup_file"
}

# URLs de acesso
show_urls() {
    echo
    print_info "🌐 URLs de acesso disponíveis:"
    echo "  📱 Interface Principal:  http://localhost:8080/"
    echo "  🎯 Gantt Dinâmico:      http://localhost:8080/gantt/"
    echo "  ⚙️  Admin Django:        http://localhost:8080/admin/"
    echo "  📊 Dashboard:           http://localhost:8080/dashboard/"
    echo "  🔧 Health Check:        http://localhost:8080/health/"
    echo
    print_info "👤 Credenciais de acesso:"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo
}

# Limpeza completa do sistema
clean_all() {
    print_warning "Esta operação irá:"
    echo "  - Parar todos os containers"
    echo "  - Remover todas as imagens do projeto"
    echo "  - Remover todos os volumes (dados serão perdidos)"
    echo "  - Limpar cache do Docker"
    echo
    read -p "Tem a certeza? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        print_info "A fazer limpeza completa..."
        docker-compose -f "$COMPOSE_FILE" down -v --rmi all
        docker system prune -f
        print_success "Limpeza completa realizada"
    else
        print_info "Operação cancelada"
    fi
}

# Menu principal
show_menu() {
    echo
    echo "Selecione uma opção:"
    echo "1)  🚀 Deploy Inicial Completo (primeira vez)"
    echo "2)  ⚡ Deploy Rápido (sem rebuild)"
    echo "3)  🔄 Restart Django (apenas web container)"
    echo "4)  🛑 Parar todos os containers"
    echo "5)  📋 Mostrar logs"
    echo "6)  📋 Seguir logs em tempo real"
    echo "7)  📊 Status dos containers"
    echo "8)  🐍 Shell Django"
    echo "9)  💾 Backup da base de dados"
    echo "10) 🧹 Limpar volumes (reset dados)"
    echo "11) 🧹 Limpeza completa do sistema"
    echo "12) 🌐 Mostrar URLs de acesso"
    echo "0)  ❌ Sair"
    echo
}

# Loop principal
main() {
    print_header

    # Verificações iniciais
    check_docker
    check_docker_compose
    check_files

    while true; do
        show_menu
        read -p "Digite sua opção (0-12): " choice
        echo

        case $choice in
            1)
                deploy_initial
                ;;
            2)
                deploy_quick
                ;;
            3)
                restart_web
                ;;
            4)
                stop_containers
                ;;
            5)
                show_logs
                ;;
            6)
                follow_logs
                ;;
            7)
                show_status
                ;;
            8)
                django_shell
                ;;
            9)
                backup_db
                ;;
            10)
                clean_volumes
                ;;
            11)
                clean_all
                ;;
            12)
                show_urls
                ;;
            0)
                print_info "A sair..."
                exit 0
                ;;
            *)
                print_error "Opção inválida: $choice"
                ;;
        esac

        echo
        read -p "Pressione Enter para continuar..."
    done
}

# Executar se chamado diretamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
