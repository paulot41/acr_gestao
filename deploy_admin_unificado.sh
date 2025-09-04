#!/bin/bash

# Script para fazer deploy das mudanças do admin unificado
echo "🚀 Iniciando deployment do Django Admin Unificado..."

# Navegar para o diretório do projeto
cd /Users/teixeira/Documents/acr_gestao

# Verificar estado do Git
echo "📋 Verificando estado do repositório..."
git status

# Adicionar todos os ficheiros modificados
echo "📁 Adicionando ficheiros modificados..."
git add core/admin.py
git add core/urls.py
git add core/templates/admin/base_site.html
git add core/templates/admin/index.html
git add acr_gestao/urls.py
git add core/web_views.py
git add core/templates/core/dashboard.html

# Fazer commit das mudanças
echo "💾 Fazendo commit das mudanças..."
git commit -m "feat: Unificar interfaces numa única admin Django modernizada

✨ Funcionalidades implementadas:
- Eliminar interfaces redundantes (dashboard web, admin integrado customizado)
- Criar Django Admin Site personalizado com dashboard integrado
- Adicionar templates modernizados com Bootstrap 5 e Bootstrap Icons
- Implementar estatísticas detalhadas por entidade (ACR/Proform)
- Adicionar auto-refresh automático a cada 5 minutos
- Badges coloridos para identificar entidades
- Ações rápidas para criar registos
- Próximas aulas com ocupação em tempo real
- Clientes recentes com fotos
- Simplificar URLs para usar apenas admin unificado
- Melhorar UX com design responsivo e moderno

🎯 Resultado: Uma única interface poderosa que substitui as três anteriores"

# Fazer push para o repositório remoto
echo "🌐 Enviando mudanças para o repositório..."
git push origin main

echo "✅ Deploy concluído! As mudanças foram enviadas para o repositório."
echo ""
echo "📋 Próximos passos:"
echo "1. Fazer pull no servidor de produção"
echo "2. Executar migrações se necessário"
echo "3. Reiniciar o servidor"
