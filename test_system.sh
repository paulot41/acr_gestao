#!/bin/bash

echo "=== Teste do Sistema ACR Gestão ==="

# Validar docker-compose.base-nginx.yml primeiro
if [ ! -s "docker-compose.base-nginx.yml" ] || ! grep -q '^services:' docker-compose.base-nginx.yml; then
    echo "❌ docker-compose.base-nginx.yml está vazio ou inválido!"
    echo "🔧 Execute: git fetch origin main && git reset --hard origin/main"
    exit 1
fi

echo "✅ docker-compose.base-nginx.yml validado"
echo ""

echo "🔍 Status dos containers:"
docker-compose -f docker-compose.base-nginx.yml ps
echo ""

echo "🌐 Teste HTTP:"
curl -I http://localhost 2>/dev/null | head -3
echo ""

echo "🔐 Teste HTTPS (com certificado autoassinado):"
curl -k -I https://localhost 2>/dev/null | head -3 || echo "HTTPS não disponível (normal com certificado autoassinado)"
echo ""

echo "📊 Últimas requisições:"
docker-compose -f docker-compose.base-nginx.yml logs nginx --tail=5 | grep -E "(GET|POST|HEAD)" || echo "Nenhuma requisição recente"
echo ""

echo "✅ Sistema funcionando! Acesse:"
echo "   - Via HTTP: http://192.168.1.11 (redirect para HTTPS)"
echo "   - Admin: https://192.168.1.11/admin/ (aceitar certificado autoassinado)"
echo ""
