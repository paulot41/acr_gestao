#!/bin/bash
# Deploy do ACR Gestão em produção local (Docker Desktop)
# Teste das otimizações do Sistema Gantt

echo "🚀 DEPLOY PRODUÇÃO LOCAL - ACR GESTÃO"
echo "====================================="

# Ir para o diretório do projeto
cd /Users/teixeira/Documents/acr_gestao

echo "1. Parando containers existentes..."
docker-compose -f docker-compose.prod.local.yml down 2>/dev/null || true

echo ""
echo "2. Limpando volumes antigos (opcional)..."
read -p "Limpar base de dados anterior? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker volume rm acr_gestao_dbdata_prod 2>/dev/null || true
    echo "✅ Volume da base de dados limpo"
fi

echo ""
echo "3. Construindo imagens Docker..."
docker-compose -f docker-compose.prod.local.yml build --no-cache

echo ""
echo "4. Iniciando serviços em produção..."
docker-compose -f docker-compose.prod.local.yml up -d

echo ""
echo "5. Aguardando inicialização dos serviços..."
sleep 30

echo ""
echo "6. Verificando estado dos serviços..."
docker-compose -f docker-compose.prod.local.yml ps

echo ""
echo "7. Criando superusuário (se necessário)..."
echo "Executar manualmente: docker-compose -f docker-compose.prod.local.yml exec web python manage.py createsuperuser"

echo ""
echo "8. Testando conectividade..."
echo "🌐 Aplicação: http://localhost"
echo "🛠️  Admin: http://localhost/admin/"
echo "📊 Sistema Gantt: http://localhost/gantt-system/"

echo ""
echo "9. Logs em tempo real:"
echo "docker-compose -f docker-compose.prod.local.yml logs -f"

echo ""
echo "✅ Deploy concluído! Teste as otimizações do Gantt em:"
echo "   http://localhost/gantt-system/"
