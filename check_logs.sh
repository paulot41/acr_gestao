#!/bin/bash

# Script rápido para verificar logs essenciais
echo "=== Verificação Rápida de Logs ACR Gestão ==="
echo ""

# Verificar se containers estão a correr
echo "🔍 Containers:"
docker-compose -f docker-compose.base-nginx.yml ps --format=table
echo ""

# Logs mais recentes do Django (onde aparecem erros 400/500)
echo "🐍 Django - Últimos logs (procurar erros 400/500):"
docker-compose -f docker-compose.base-nginx.yml logs web --tail=10
echo ""

# Logs do Nginx com códigos HTTP
echo "🌐 Nginx - Requisições recentes (códigos HTTP):"
docker-compose -f docker-compose.base-nginx.yml logs nginx --tail=10 | grep -E "(GET|POST|HEAD)" || echo "Nenhuma requisição recente"
echo ""

# Verificar se há erros críticos
echo "⚠️ Erros críticos recentes:"
docker-compose -f docker-compose.base-nginx.yml logs --tail=20 | grep -i "error\|exception\|500\|400" | tail -5 || echo "Nenhum erro crítico encontrado"
echo ""

echo "✅ Verificação concluída!"
echo "💡 Para logs em tempo real: docker-compose -f docker-compose.base-nginx.yml logs -f"
