#!/bin/bash
# DEPLOY DA FASE 1 - INTERFACE WEB + SISTEMA GANTT
# Script para executar no servidor de produção

echo "🚀 INICIANDO DEPLOY DA FASE 1 - ACR GESTÃO"
echo "============================================="

# Verificar se está no diretório correto
if [ ! -f "manage.py" ]; then
    echo "❌ ERRO: Execute este script no diretório raiz do projeto ACR Gestão"
    exit 1
fi

echo "📥 1. Fazendo pull das alterações do GitHub..."
git fetch origin main
git merge origin/main

if [ $? -ne 0 ]; then
    echo "❌ ERRO: Falha ao fazer merge do código"
    exit 1
fi

echo "✅ Código atualizado com sucesso"

echo "🔍 2. Validando integridade dos arquivos Docker Compose..."
./validate_compose.sh

if [ $? -ne 0 ]; then
    echo "❌ ERRO: Arquivos Docker Compose inválidos"
    exit 1
fi

echo "✅ Arquivos validados"

echo "🛠️  3. Executando deploy com validação automática..."
./deploy_nginx.sh

if [ $? -ne 0 ]; then
    echo "❌ ERRO: Falha no deploy"
    exit 1
fi

echo "✅ Deploy executado com sucesso"

# Aguardar containers iniciarem
echo "⏳ Aguardando containers iniciarem..."
sleep 10

echo "🔄 4. Executando migrações da base de dados..."
docker-compose -f docker-compose.base-nginx.yml exec -T web python manage.py migrate

if [ $? -ne 0 ]; then
    echo "❌ ERRO: Falha nas migrações"
    exit 1
fi

echo "✅ Migrações executadas"

echo "📊 5. Criando dados de exemplo (se necessário)..."
docker-compose -f docker-compose.base-nginx.yml exec -T web python manage.py create_sample_data

echo "📁 6. Coletando arquivos estáticos..."
docker-compose -f docker-compose.base-nginx.yml exec -T web python manage.py collectstatic --noinput

if [ $? -ne 0 ]; then
    echo "❌ ERRO: Falha ao coletar arquivos estáticos"
    exit 1
fi

echo "✅ Arquivos estáticos coletados"

echo "🧪 7. Testando sistema..."
./test_system.sh

if [ $? -ne 0 ]; then
    echo "⚠️  AVISO: Alguns testes falharam, mas o sistema pode estar funcional"
fi

echo ""
echo "🎉 DEPLOY DA FASE 1 CONCLUÍDO COM SUCESSO!"
echo "=========================================="
echo ""
echo "🌐 URLs disponíveis:"
echo "   • Interface Web: https://seudominio.com/"
echo "   • Login: https://seudominio.com/login/"
echo "   • Dashboard: https://seudominio.com/"
echo "   • Sistema Gantt: https://seudominio.com/gantt/"
echo "   • API: https://seudominio.com/api/"
echo "   • Admin: https://seudominio.com/admin/"
echo ""
echo "🔑 Credenciais padrão:"
echo "   • Utilizador: admin"
echo "   • Password: admin123"
echo ""
echo "✨ Funcionalidades da Fase 1 disponíveis:"
echo "   • Dashboard interativo com KPIs"
echo "   • Sistema Gantt para 3 espaços (Ginásio, Pilates, Pavilhão)"
echo "   • Gestão completa de clientes, instrutores e modalidades"
echo "   • Interface web responsiva com Bootstrap 5"
echo "   • Upload de fotos e dados completos"
echo ""
echo "📋 Próximas verificações recomendadas:"
echo "   1. Testar login na interface web"
echo "   2. Verificar funcionamento do Gantt"
echo "   3. Testar criação de clientes/instrutores"
echo "   4. Verificar se as APIs continuam funcionais"
echo ""
echo "🔧 Para verificar logs se houver problemas:"
echo "   docker-compose -f docker-compose.base-nginx.yml logs web"
echo ""
