#!/bin/bash

echo "=== ACR Gestão - Monitor do Sistema ==="
echo "Data: $(date)"
echo ""

# Status dos containers
echo "📦 Status dos Containers:"
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
echo ""

# Health status
echo "🏥 Health Checks:"
for service in web db caddy; do
    health=$(docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps --format "table {{.Service}}\t{{.Status}}" | grep $service | awk '{print $2}')
    if [[ $health == *"healthy"* ]]; then
        echo "✅ $service: OK"
    else
        echo "❌ $service: $health"
    fi
done
echo ""

# Uso de recursos
echo "💾 Uso de Recursos:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" | grep -E "(acr_gestao|NAME)"
echo ""

# Logs recentes (últimas 10 linhas)
echo "📋 Logs Recentes (últimas 10 linhas):"
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=10 web
echo ""

# Espaço em disco
echo "💿 Espaço em Disco:"
df -h | grep -E "(Filesystem|/dev/)"
echo ""

# Verificar conectividade
echo "🌐 Teste de Conectividade:"
for domain in acrsantatecla.duckdns.org proformsc.duckdns.org; do
    if curl -s -I https://$domain | grep -q "200 OK"; then
        echo "✅ $domain: Acessível"
    else
        echo "❌ $domain: Inacessível"
    fi
done
echo ""

# Backups recentes
echo "💾 Backups Recentes:"
if [ -d "./backups" ]; then
    ls -la ./backups/ | tail -5
else
    echo "❌ Diretório de backups não encontrado"
fi
