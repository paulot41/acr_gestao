#!/bin/bash

echo "=== Diagnóstico e Correção do Erro 400 ==="
echo ""

# Verificar se .env.prod existe no servidor
if [ ! -f ".env.prod" ]; then
    echo "❌ Arquivo .env.prod não encontrado no servidor!"
    echo "🔧 Copie .env.prod.example para .env.prod e configure"
    exit 1
fi

echo "✅ Arquivo .env.prod encontrado"
echo ""

# Verificar conteúdo do ALLOWED_HOSTS
echo "🔍 Verificando ALLOWED_HOSTS atual:"
grep "ALLOWED_HOSTS" .env.prod || echo "❌ ALLOWED_HOSTS não encontrado!"
echo ""

# Verificar se 192.168.1.11 está incluído
if grep -q "192.168.1.11" .env.prod; then
    echo "✅ IP 192.168.1.11 está incluído no .env.prod"
else
    echo "❌ IP 192.168.1.11 NÃO está incluído no .env.prod"
    echo "🔧 Será necessário atualizar o arquivo"
fi
echo ""

# Verificar se o container web carregou a configuração
echo "🐍 Verificando se Django carregou a configuração:"
docker-compose -f docker-compose.base-nginx.yml exec web python -c "
import os
from django.conf import settings
print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)
print('DEBUG:', settings.DEBUG)
" 2>/dev/null || echo "❌ Não foi possível verificar configuração Django"
echo ""

# Verificar logs de erro específicos
echo "⚠️ Últimos erros de ALLOWED_HOSTS:"
docker-compose -f docker-compose.base-nginx.yml logs web --tail=50 | grep -i "disallowedhost\|allowed_hosts" | tail -3
echo ""

# Sugerir correção
echo "🔧 SOLUÇÕES POSSÍVEIS:"
echo "======================"
echo "1. Verificar se .env.prod tem ALLOWED_HOSTS correto:"
echo "   grep ALLOWED_HOSTS .env.prod"
echo ""
echo "2. Se não tiver 192.168.1.11, adicionar:"
echo "   sed -i 's/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=acrsantatecla.duckdns.org,proformsc.duckdns.org,192.168.1.11,localhost/' .env.prod"
echo ""
echo "3. Reiniciar container web para carregar nova configuração:"
echo "   docker-compose -f docker-compose.base-nginx.yml restart web"
echo ""
echo "4. Verificar se funcionou:"
echo "   curl -I http://192.168.1.11"
echo ""
echo "5. Se ainda não funcionar, rebuild completo:"
echo "   docker-compose -f docker-compose.base-nginx.yml down"
echo "   docker-compose -f docker-compose.base-nginx.yml up -d"
