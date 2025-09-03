#!/bin/bash

echo "=== Validação de Arquivos Docker Compose ==="

COMPOSE_FILE="docker-compose.base-nginx.yml"
EXIT_CODE=0

# Verificar se arquivo existe
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ $COMPOSE_FILE não encontrado!"
    EXIT_CODE=1
fi

# Verificar se arquivo não está vazio
if [ ! -s "$COMPOSE_FILE" ]; then
    echo "❌ $COMPOSE_FILE está vazio!"
    EXIT_CODE=1
fi

# Verificar se contém seção services
if [ -f "$COMPOSE_FILE" ] && ! grep -q '^services:' "$COMPOSE_FILE"; then
    echo "❌ $COMPOSE_FILE não contém seção 'services'!"
    EXIT_CODE=1
fi

# Validar sintaxe YAML com docker-compose
if command -v docker-compose >/dev/null 2>&1; then
    echo "🔍 Validando sintaxe YAML..."
    if ! docker-compose -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
        echo "❌ $COMPOSE_FILE contém erros de sintaxe YAML!"
        EXIT_CODE=1
    else
        echo "✅ Sintaxe YAML válida"
    fi
else
    echo "⚠️  docker-compose não encontrado, pulando validação de sintaxe"
fi

# Verificar serviços essenciais
REQUIRED_SERVICES=("web" "db" "nginx")
for service in "${REQUIRED_SERVICES[@]}"; do
    if ! grep -q "^  $service:" "$COMPOSE_FILE"; then
        echo "❌ Serviço '$service' não encontrado em $COMPOSE_FILE!"
        EXIT_CODE=1
    else
        echo "✅ Serviço '$service' encontrado"
    fi
done

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Todos os arquivos Docker Compose são válidos!"
else
    echo "❌ Problemas encontrados nos arquivos Docker Compose!"
    echo "🔧 Para corrigir, execute: git fetch origin main && git reset --hard origin/main"
fi

exit $EXIT_CODE
