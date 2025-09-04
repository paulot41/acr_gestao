#!/bin/bash

# Script para fazer pull das mudanças do Django Admin Unificado no servidor de produção
echo "🚀 Atualizando servidor de produção com Django Admin Unificado..."

# Navegar para o diretório do projeto no servidor
cd /home/$USER/acr_gestao || { echo "❌ Diretório do projeto não encontrado!"; exit 1; }

echo "📋 Verificando estado atual..."
git status

echo "🔄 Fazendo pull das mudanças..."
git fetch origin main
git pull origin main

echo "📦 Verificando se há migrações pendentes..."
python manage.py showmigrations --plan

echo "⚡ Aplicando migrações (se necessárias)..."
python manage.py migrate

echo "📁 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "🔄 Reiniciando containers Docker..."
docker-compose -f docker-compose.nginx.yml down
docker-compose -f docker-compose.nginx.yml up -d

echo "✅ Deploy concluído!"
echo ""
echo "🌐 Aceda à nova interface unificada em: https://seu-dominio.com/admin/"
echo ""
echo "✨ Funcionalidades implementadas:"
echo "   - Django Admin Site personalizado com dashboard integrado"
echo "   - Estatísticas detalhadas por entidade (ACR/Proform)"
echo "   - Auto-refresh automático a cada 5 minutos"
echo "   - Interface moderna com Bootstrap 5"
echo "   - Badges coloridos para identificar entidades"
echo "   - Ações rápidas para criar registos"
echo "   - Design responsivo e moderno"
