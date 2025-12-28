# ACR Gestão - Makefile para Docker Desktop
# Comandos simplificados para desenvolvimento

.PHONY: help validate quick-start deploy status logs clean test lint format format-check

# Configurações
COMPOSE_FILE = docker-compose.base-nginx.yml

help: ## Mostrar esta ajuda
	@echo "🚀 ACR Gestão - Comandos Docker Desktop"
	@echo "========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

validate: ## Validar sistema antes do deploy
	@./validate_setup.sh

quick-start: ## Deploy rápido automático (primeira vez)
	@./quick_start.sh

deploy: ## Deploy interativo com opções
	@./deploy_local.sh

status: ## Ver status dos containers
	@echo "📊 Status dos containers:"
	@docker-compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "📊 Recursos utilizados:"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

logs: ## Ver logs dos containers
	@docker-compose -f $(COMPOSE_FILE) logs --tail=50

logs-follow: ## Seguir logs em tempo real
	@docker-compose -f $(COMPOSE_FILE) logs -f

stop: ## Parar todos os containers
	@echo "🛑 Parando containers..."
	@docker-compose -f $(COMPOSE_FILE) down

start: ## Iniciar containers (se já foram criados)
	@echo "▶️  Iniciando containers..."
	@docker-compose -f $(COMPOSE_FILE) up -d

restart: ## Reiniciar containers
	@echo "🔄 Reiniciando containers..."
	@docker-compose -f $(COMPOSE_FILE) restart

restart-web: ## Reiniciar apenas o Django
	@echo "🔄 Reiniciando Django..."
	@docker-compose -f $(COMPOSE_FILE) restart web

shell: ## Abrir shell Django
	@docker-compose -f $(COMPOSE_FILE) exec web python manage.py shell

migrate: ## Executar migrações
	@docker-compose -f $(COMPOSE_FILE) exec web python manage.py migrate

collectstatic: ## Recolher ficheiros estáticos
	@docker-compose -f $(COMPOSE_FILE) exec web python manage.py collectstatic --noinput

backup: ## Backup da base de dados
	@mkdir -p backups
	@docker-compose -f $(COMPOSE_FILE) exec db pg_dump -U acruser -d acrdb_local > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "💾 Backup criado em backups/"

clean: ## Limpar containers e volumes (CUIDADO: apaga dados)
	@echo "⚠️  Esta operação irá apagar TODOS os dados!"
	@read -p "Continuar? (s/N): " CONFIRM && [ "$$CONFIRM" = "s" ] || exit 1
	@docker-compose -f $(COMPOSE_FILE) down -v
	@docker system prune -f
	@echo "🧹 Sistema limpo"

urls: ## Mostrar URLs de acesso
	@echo "🌐 URLs disponíveis:"
	@echo "  📱 Interface:     http://localhost:8080/"
	@echo "  🎯 Gantt:        http://localhost:8080/gantt/"
	@echo "  ⚙️  Admin:        http://localhost:8080/admin/"
	@echo "  📊 Dashboard:    http://localhost:8080/dashboard/"
	@echo "  🔧 Health:       http://localhost:8080/health/"
	@echo ""
	@echo "👤 Credenciais: admin / admin123"

build: ## Build das imagens Docker
	@echo "🔨 Fazendo build das imagens..."
	@docker-compose -f $(COMPOSE_FILE) build --no-cache

up: ## Iniciar em background
	@docker-compose -f $(COMPOSE_FILE) up -d

down: ## Parar e remover containers
	@docker-compose -f $(COMPOSE_FILE) down

reset: clean quick-start ## Reset completo: limpar + deploy inicial

test: ## Executar testes
	@pytest

lint: ## Lint com ruff (requer requirements-dev.txt instalado)
	@ruff check .

format: ## Formatar com ruff (requer requirements-dev.txt instalado)
	@ruff format .

format-check: ## Verificar formatação (sem alterar ficheiros)
	@ruff format --check .
