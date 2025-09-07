#!/bin/bash

echo "=== Diagnóstico e Resolução do Container ACR Gestão ==="
echo ""

echo "1. Verificando containers em execução..."
docker ps

echo ""
echo "2. Verificando todos os containers (incluindo parados)..."
docker ps -a

echo ""
echo "3. Verificando logs do container web..."
docker-compose logs --tail=10 web

echo ""
echo "4. Verificando se a porta 8000 está ocupada..."
lsof -i :8000

echo ""
echo "5. Verificando estado dos serviços..."
docker-compose ps

echo ""
echo "=== Tentativa de Resolução ==="

echo "6. Parando todos os containers..."
docker-compose down

echo ""
echo "7. Aplicando as alterações do dashboard e reiniciando..."
docker-compose up -d --build

echo ""
echo "8. Aguardando containers ficarem prontos..."
sleep 10

echo ""
echo "9. Verificando estado final..."
docker-compose ps

echo ""
echo "10. Testando acesso..."
curl -I http://localhost:8000 2>/dev/null || echo "Acesso falhado - verificar logs"

echo ""
echo "=== Instruções ==="
echo "Acesse: http://localhost:8000"
echo "Admin: http://localhost:8000/admin/"
echo "Dashboard: http://localhost:8000/dashboard/ (redireciona para Gantt)"
echo ""
echo "Se ainda não funcionar, execute:"
echo "docker-compose logs web"
