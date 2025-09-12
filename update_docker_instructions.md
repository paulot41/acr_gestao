# Instruções para Atualizar Docker com as Alterações do Dashboard

## Alterações Implementadas
- ✅ Dashboard views simplificadas em `core/dashboard_views.py`
- ✅ Template atualizado em `core/templates/core/dashboard_simple.html`
- ✅ CRUD disponível via páginas web e também no Django Admin
- ✅ Dashboard focado em consulta e marcação de aulas

### Atualizações recentes

- Substituição de `except Exception` por exceções específicas com logging.
- Remoção da criação automática de organização em `get_current_organization`.
- Middleware de multi-tenancy consolidado.
- Cálculos financeiros com `Decimal`.
- Migração para `UniqueConstraint`.
- Remoção de imports desnecessários.
- Novos testes automatizados para modelos e middleware.

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
