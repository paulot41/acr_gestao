# Instruções para Atualizar Docker com as Alterações do Dashboard

## Alterações Implementadas
- ✅ Dashboard views simplificado em `core/dashboard_views.py`
- ✅ Template unificado criado em `core/templates/core/dashboard_simple.html`
- ✅ Todas as operações CRUD redirecionadas para Django Admin
- ✅ Dashboard focado apenas em consulta e marcação de aulas

## Como Aplicar as Alterações no Docker Desktop

### Opção 1: Redeploy Completo (Recomendado)
```bash
cd /Users/teixeira/Documents/acr_gestao
docker-compose down
docker-compose up --build -d
```

### Opção 2: Restart dos Containers
```bash
cd /Users/teixeira/Documents/acr_gestao
docker-compose restart web
```

### Opção 3: Usar Script de Deploy
```bash
cd /Users/teixeira/Documents/acr_gestao
./redeploy.sh
```

## Verificação
Após aplicar as alterações:
1. Aceder ao dashboard em: http://localhost:8000/dashboard/
2. Verificar que redireciona para o Gantt
3. Testar diferentes tipos de utilizador
4. Confirmar link para Django Admin (/admin/)

## Funcionalidades do Novo Dashboard
- **Admin**: Estatísticas gerais + link para Django Admin
- **Instrutor**: Suas aulas de hoje e próximas
- **Cliente**: Reservas e créditos
- **Staff**: Atividade diária + link para Django Admin

## Resolução de Problemas
Se houver erros:
1. Verificar logs: `docker-compose logs web`
2. Reiniciar: `docker-compose restart`
3. Rebuild: `docker-compose up --build`
