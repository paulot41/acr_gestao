#!/bin/bash
# Script de redeploy após alterações de código

echo "🔄 REDEPLOY APÓS ALTERAÇÕES - ACR GESTÃO"
echo "======================================="

cd /Users/teixeira/Documents/acr_gestao

echo "1. Parando containers..."
docker-compose -f docker-compose.prod.local.yml down

echo ""
echo "2. Rebuilding imagem web com alterações..."
docker-compose -f docker-compose.prod.local.yml build --no-cache web

echo ""
echo "3. Reiniciando serviços..."
docker-compose -f docker-compose.prod.local.yml up -d

echo ""
echo "4. Aguardando inicialização..."
sleep 10

echo ""
echo "5. Verificando estado dos serviços..."
docker-compose -f docker-compose.prod.local.yml ps

echo ""
echo "6. Testando conectividade..."
curl -s -o /dev/null -w "Status: %{http_code}, Tempo: %{time_total}s\n" http://localhost/

echo ""
echo "✅ Redeploy concluído!"
echo "🌐 Aplicação: http://localhost"
echo "📊 Sistema Gantt: http://localhost/gantt-system/"
