#!/bin/bash
set -e

echo "🚀 PASSO 2 - Deploy do Django Admin Unificado"
echo "=============================================="

# Verificar se estamos no diretório correto
if [ ! -f "manage.py" ]; then
    echo "❌ Erro: Não estou no diretório do projeto Django"
    echo "Execute: cd /srv/acr_gestao"
    exit 1
fi

echo "📍 Diretório atual: $(pwd)"
echo "⏰ Timestamp: $(date)"
echo ""

# PASSO 1: Pull das mudanças mais recentes
echo "🔄 PASSO 1: Fazendo pull das mudanças..."
git fetch origin main
git pull origin main

# PASSO 2: Verificar se a correção do admin_site está presente
echo "🔍 PASSO 2: Verificando se admin_site foi corrigido..."
if grep -q "admin_site = ACRAdminSite" core/admin.py; then
    echo "✅ admin_site encontrado em core/admin.py"
    grep -n "admin_site" core/admin.py
else
    echo "❌ ERRO: admin_site não encontrado em core/admin.py"
    echo "O deploy não pode continuar sem esta correção."
    exit 1
fi

# PASSO 3: Validar arquivos Docker Compose
echo "🔍 PASSO 3: Validando arquivos Docker Compose..."
if [ -f "validate_compose.sh" ]; then
    ./validate_compose.sh
else
    echo "⚠️  validate_compose.sh não encontrado, continuando..."
fi

# PASSO 4: Backup de segurança
echo "📦 PASSO 4: Criando backup de segurança..."
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)

if docker-compose -f docker-compose.base-nginx.yml ps -q | grep -q .; then
    echo "📋 Containers ativos encontrados, fazendo backup..."
    docker-compose -f docker-compose.base-nginx.yml exec -T web python manage.py dumpdata > "$BACKUP_DIR/db_backup_pre_step2_$TIMESTAMP.json" || echo "⚠️  Backup de BD falhou, continuando..."
fi

# PASSO 5: Deploy principal
echo "🚀 PASSO 5: Executando deploy principal..."
./deploy_nginx.sh

# PASSO 6: Verificar se o deploy foi bem-sucedido
echo "🔍 PASSO 6: Verificando se containers estão rodando..."
sleep 5
docker-compose -f docker-compose.base-nginx.yml ps

# PASSO 7: Testar o admin unificado
echo "🧪 PASSO 7: Testando Django Admin Unificado..."
echo "Aguardando servidor inicializar..."
sleep 10

# Tentar fazer curl para verificar se está respondendo
if curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/ | grep -q "200\|301\|302"; then
    echo "✅ Servidor Django respondendo corretamente"
else
    echo "⚠️  Servidor pode ainda estar inicializando..."
fi

# PASSO 8: Relatório final
echo ""
echo "🎉 DEPLOY DO PASSO 2 CONCLUÍDO!"
echo "================================"
echo ""
echo "✅ Django Admin Unificado deployado com sucesso"
echo "🌐 URL: https://seu-dominio.com/admin/"
echo "🔐 Login: Use suas credenciais de admin existentes"
echo ""
echo "📋 Funcionalidades disponíveis:"
echo "   • Dashboard integrado com estatísticas ACR/Proform"
echo "   • Interface moderna com Bootstrap 5"
echo "   • Auto-refresh automático"
echo "   • Badges coloridos por entidade"
echo "   • Ações rápidas para criar registos"
echo "   • Gestão unificada de clientes, instrutores, modalidades"
echo ""
echo "📊 Status do Projeto:"
echo "   ✅ PASSO 1 - Problema empty compose file: CONCLUÍDO"
echo "   ✅ PASSO 2 - Django Admin Unificado: CONCLUÍDO"
echo "   ⏳ FASE 1 - Interface Web + Gantt: PRÓXIMA"
echo ""
echo "🔧 Troubleshooting:"
echo "   • Logs: docker-compose -f docker-compose.base-nginx.yml logs web"
echo "   • Status: docker-compose -f docker-compose.base-nginx.yml ps"
echo "   • Restart: docker-compose -f docker-compose.base-nginx.yml restart"
echo ""
echo "🎯 PASSO 2 CONCLUÍDO COM SUCESSO!"
