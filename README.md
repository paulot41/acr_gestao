# ACR Gestão - Sistema de Gestão Multi-Tenant

Sistema de gestão para academias e centros de fitness com suporte a múltiplas organizações.

## 🚀 Deploy para Produção

### Pré-requisitos
- Docker e Docker Compose instalados
- Domínios configurados (DNS apontando para o servidor)

### 1. Configuração Inicial

1. Clone o repositório e navegue para o diretório:
```bash
cd acr_gestao
```

2. Configure as variáveis de ambiente:
```bash
cp .env.prod.example .env.prod
```

3. Edite o arquivo `.env.prod` com suas configurações:
```bash
# Gere uma SECRET_KEY segura:
python -c 'import secrets; print(secrets.token_urlsafe(50))'

# Configure os outros valores no .env.prod
```

### 2. Deploy Automático

Execute o script de deploy:
```bash
./deploy.sh
```

### 3. Configuração Pós-Deploy

1. Criar superusuário:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py setup_production --create-superuser
```

2. Criar organizações:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py setup_production --create-org acrsantatecla.duckdns.org --org-name "ACR Santa Tecla"
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py setup_production --create-org proformsc.duckdns.org --org-name "Proform SC"
```

## 📊 Monitoramento

### Verificar Status do Sistema
```bash
./monitor.sh
```

### Logs em Tempo Real
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### Backup Manual
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec db pg_dump -U acruser acrdb | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restaurar Backup
```bash
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db psql -U acruser -d acrdb
```

## 🔧 Manutenção

### Atualizar Sistema
```bash
git pull origin main
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Executar Migrações
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate
```

### Coletar Arquivos Estáticos
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

## 🛠️ Desenvolvimento Local

### Configuração
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Com Docker
```bash
docker-compose -f docker-compose.dev.yml up
```

## 📁 Estrutura do Projeto

```
acr_gestao/
├── core/                    # App principal
│   ├── models.py           # Modelos de dados
│   ├── api.py              # APIs REST
│   ├── middleware.py       # Middleware multitenant
│   └── management/         # Comandos customizados
├── templates/              # Templates HTML
├── static/                 # Arquivos estáticos
├── docker-compose.yml      # Configuração Docker base
├── docker-compose.prod.yml # Sobrescrita para produção
├── Caddyfile              # Configuração do proxy
├── deploy.sh              # Script de deploy
└── monitor.sh             # Script de monitoramento
```

## 🏗️ Arquitetura

### Multi-Tenancy
- Cada organização é identificada pelo domínio
- Middleware intercepta requests e filtra dados por organização
- Modelos incluem foreign key para Organization

### Componentes
- **Django**: Framework web principal
- **PostgreSQL**: Base de dados
- **Caddy**: Proxy reverso com HTTPS automático
- **Gunicorn**: Servidor WSGI para produção

## 🔐 Segurança

### Implementado
- ✅ HTTPS obrigatório em produção
- ✅ Headers de segurança (HSTS, CSP, etc.)
- ✅ Cookies seguros
- ✅ Validação de domínios permitidos
- ✅ Usuário não-root no container

### Recomendações Adicionais
- Configure firewall no servidor
- Use certificados SSL válidos
- Monitore logs regularmente
- Mantenha backups atualizados

## 📞 Suporte

Para problemas ou dúvidas, verifique:
1. Logs do sistema: `./monitor.sh`
2. Status dos containers: `docker-compose ps`
3. Conectividade: teste os domínios no navegador

## 📝 Notas de Versão

### v1.0.0 (Produção Inicial)
- Sistema multitenant funcional
- APIs REST para gestão
- Deploy automatizado
- Monitoramento básico
- Backup automático
