#!/bin/bash

echo "=== Monitor ACR Gestão - Verificação Completa ==="
echo "$(date)"
echo ""

# Validar docker-compose.base-nginx.yml primeiro
if [ ! -s "docker-compose.base-nginx.yml" ] || ! grep -q '^services:' docker-compose.base-nginx.yml; then
    echo "❌ docker-compose.base-nginx.yml está vazio ou inválido!"
    echo "🔧 Execute: git fetch origin main && git reset --hard origin/main"
    exit 1
fi

echo "✅ docker-compose.base-nginx.yml validado"
echo ""

echo "🔍 STATUS DOS CONTAINERS:"
echo "=========================="
docker-compose -f docker-compose.base-nginx.yml ps
echo ""

echo "🌐 TESTE DE CONECTIVIDADE:"
echo "=========================="
echo "HTTP (deve redirecionar 301):"
curl -I http://localhost 2>/dev/null | head -3 || echo "❌ HTTP não responde"
echo ""
echo "HTTPS (certificado autoassinado):"
curl -k -I https://localhost 2>/dev/null | head -3 || echo "❌ HTTPS não responde"
echo ""

echo "📊 LOGS DO NGINX (últimas 10 linhas):"
echo "====================================="
docker-compose -f docker-compose.base-nginx.yml logs nginx --tail=10
echo ""

echo "🐍 LOGS DO DJANGO/WEB (últimas 15 linhas):"
echo "=========================================="
docker-compose -f docker-compose.base-nginx.yml logs web --tail=15
echo ""

echo "🗄️ LOGS DA BASE DE DADOS (últimas 5 linhas):"
echo "============================================="
docker-compose -f docker-compose.base-nginx.yml logs db --tail=5
echo ""

echo "🔥 ÚLTIMAS REQUISIÇÕES HTTP:"
echo "==========================="
docker-compose -f docker-compose.base-nginx.yml logs nginx --tail=20 | grep -E "(GET|POST|HEAD|PUT|DELETE)" | tail -10 || echo "Nenhuma requisição HTTP recente"
echo ""

echo "⚠️ ERROS RECENTES:"
echo "=================="
echo "Erros no Django:"
docker-compose -f docker-compose.base-nginx.yml logs web --tail=50 | grep -i "error\|exception\|traceback" | tail -5 || echo "Nenhum erro Django recente"
echo ""
echo "Erros no Nginx:"
docker-compose -f docker-compose.base-nginx.yml logs nginx --tail=50 | grep -i "error" | tail -5 || echo "Nenhum erro Nginx recente"
echo ""

echo "💾 UTILIZAÇÃO DE RECURSOS:"
echo "=========================="
echo "Containers em execução:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" $(docker-compose -f docker-compose.base-nginx.yml ps -q) 2>/dev/null || echo "Não foi possível obter estatísticas de recursos"
echo ""

echo "🔍 HEALTH CHECKS:"
echo "=================="
WEB_HEALTH=$(docker-compose -f docker-compose.base-nginx.yml ps web | grep -o "(healthy\|health: starting\|unhealthy)" || echo "N/A")
DB_HEALTH=$(docker-compose -f docker-compose.base-nginx.yml ps db | grep -o "(healthy\|health: starting\|unhealthy)" || echo "N/A")
echo "Web: $WEB_HEALTH"
echo "DB: $DB_HEALTH"
echo ""

echo "✅ RESUMO:"
echo "=========="
RUNNING_CONTAINERS=$(docker-compose -f docker-compose.base-nginx.yml ps --services | wc -l)
UP_CONTAINERS=$(docker-compose -f docker-compose.base-nginx.yml ps | grep "Up" | wc -l)

if [ "$UP_CONTAINERS" -eq 3 ]; then
    echo "✅ Todos os serviços estão em execução ($UP_CONTAINERS/3)"
    echo "🌐 Acesse:"
    echo "   - HTTP: http://192.168.1.11 (deve redirecionar)"
    echo "   - HTTPS: https://192.168.1.11 (aceitar certificado)"
    echo "   - Admin: https://192.168.1.11/admin/"
else
    echo "⚠️ Alguns serviços podem não estar funcionando ($UP_CONTAINERS/3)"
fi

echo ""
echo "📊 Para monitorização contínua:"
echo "   docker-compose -f docker-compose.base-nginx.yml logs -f"
echo ""
echo "🔄 Para reiniciar se necessário:"
echo "   docker-compose -f docker-compose.base-nginx.yml restart"
