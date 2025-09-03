#!/bin/bash

echo "=== Script de Recuperação ACR Gestão ==="

COMPOSE_FILE="docker-compose.base-nginx.yml"
BACKUP_DIR="backups"

# Função para restaurar do Git
restore_from_git() {
    echo "🔄 Restaurando $COMPOSE_FILE do repositório Git..."
    git fetch origin main
    git checkout origin/main -- "$COMPOSE_FILE"
    echo "✅ $COMPOSE_FILE restaurado do Git"
}

# Função para restaurar do backup mais recente
restore_from_backup() {
    echo "🔍 Procurando backup mais recente..."
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/$COMPOSE_FILE.*.bak 2>/dev/null | head -n1)

    if [ -n "$LATEST_BACKUP" ]; then
        echo "📁 Backup encontrado: $LATEST_BACKUP"
        cp "$LATEST_BACKUP" "$COMPOSE_FILE"
        echo "✅ $COMPOSE_FILE restaurado do backup"
        return 0
    else
        echo "❌ Nenhum backup encontrado"
        return 1
    fi
}

# Verificar se precisa de recuperação
if [ -s "$COMPOSE_FILE" ] && grep -q '^services:' "$COMPOSE_FILE"; then
    echo "✅ $COMPOSE_FILE está íntegro, nenhuma recuperação necessária"
    exit 0
fi

echo "⚠️  $COMPOSE_FILE está corrompido ou vazio, iniciando recuperação..."

# Tentar restaurar do Git primeiro
if restore_from_git; then
    # Validar se a restauração funcionou
    if [ -s "$COMPOSE_FILE" ] && grep -q '^services:' "$COMPOSE_FILE"; then
        echo "✅ Recuperação do Git bem-sucedida!"
        exit 0
    fi
fi

# Se Git falhou, tentar backup
echo "⚠️  Restauração do Git falhou, tentando backup..."
if restore_from_backup; then
    # Validar se a restauração funcionou
    if [ -s "$COMPOSE_FILE" ] && grep -q '^services:' "$COMPOSE_FILE"; then
        echo "✅ Recuperação do backup bem-sucedida!"
        exit 0
    fi
fi

echo "❌ Todas as tentativas de recuperação falharam!"
echo "🆘 Ação manual necessária:"
echo "   1. Verifique a conectividade com o repositório Git"
echo "   2. Restaure manualmente de um backup conhecido"
echo "   3. Recrie o arquivo a partir de outro ambiente"
exit 1
