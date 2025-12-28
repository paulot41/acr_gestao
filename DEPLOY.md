# 🚀 Guia de Deploy - Produção & Desenvolvimento

## 📋 **TIPOS DE DEPLOY DISPONÍVEIS**

Este projeto suporta **dois tipos de deploy**:
- 🏭 **PRODUÇÃO (Debian/Ubuntu)** - Deploy completo com SSL e domínios
- 💻 **DESENVOLVIMENTO LOCAL (Docker Desktop)** - Testes e desenvolvimento

### Atualizações recentes

- Substituição de blocos `except Exception` por exceções específicas com logging.
- Remoção da criação automática de organização em `get_current_organization`.
- Middleware de multi-tenancy consolidado.
- Cálculos monetários com `Decimal`.
- Migração para `UniqueConstraint` no modelo `Person` (restantes modelos mantêm `unique_together`).
- Limpeza de imports redundantes.
- Novos testes automatizados para garantir estabilidade.

---

## 💻 **DEPLOY LOCAL - Docker Desktop (Desenvolvimento/Testes)**

### ✨ **Funcionalidades do Deploy Local**
- 🎯 **Gantt Dinâmico** com drag & drop para criação de aulas
- 👥 **Sistema de Turmas** completo integrado
- 🔄 **APIs otimizadas** para performance máxima
- 📱 **Interface responsiva** moderna
- ⚡ **Validações em tempo real** de conflitos
- 🎨 **Personalização por modalidade** (cores, durações)

### 📋 **Pré-requisitos para Docker Desktop**

#### 1. Docker Desktop instalado
```bash
# Verificar se Docker está instalado e funcionando
docker --version
docker-compose --version

# Deve retornar versões válidas (ex: Docker version 24.x, Docker Compose v2.x)
```

#### 2. Git (para clonar o repositório)
```bash
# macOS (se não tiver)
brew install git

# Verificar
git --version
```

### 🚀 **Deploy Local Rápido**

#### 1. Clonar e configurar projeto
```bash
# Clonar repositório
git clone https://github.com/paulot41/acr_gestao.git
cd acr_gestao

# Verificar ficheiros necessários
ls -la deploy*.sh docker-compose*.yml nginx.conf
```

#### 2. Configuração automática para desenvolvimento
```bash
# Criar ficheiro de configuração local
cat > .env << 'EOF'
# ACR Gestão - Configuração Docker Desktop (Desenvolvimento)
SECRET_KEY=django-insecure-local-dev-key-change-in-production-12345
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database PostgreSQL (Docker)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=acrdb_local
DB_USER=acruser
DB_PASSWORD=acrpass123
DB_HOST=db
DB_PORT=5432

# PostgreSQL Container
POSTGRES_DB=acrdb_local
POSTGRES_USER=acruser
POSTGRES_PASSWORD=acrpass123

# Redis Cache
REDIS_URL=redis://redis:6379/0

# Superuser para desenvolvimento
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@acr.local
DJANGO_SUPERUSER_PASSWORD=admin123

# Multi-tenant domains (desenvolvimento)
ACR_DOMAIN=localhost
PROFORM_DOMAIN=127.0.0.1

# Timezone
TIME_ZONE=Europe/Lisbon
USE_TZ=1
EOF

echo "✅ Configuração local criada"
```

#### 3. Deploy com script automático
```bash
# Tornar script executável
chmod +x deploy_nginx.sh

# Deploy local (sem SSL, para desenvolvimento)
./deploy_nginx.sh --local

# OU deploy manual:
docker-compose -f docker-compose.base-nginx.yml up -d --build
```

#### 4. Aguardar inicialização completa
```bash
# Monitorizar logs
docker-compose -f docker-compose.base-nginx.yml logs -f

# Aguardar até ver:
# ✅ "web_1    | Django development server is running"
# ✅ "nginx_1  | Configuration test passed"
# ✅ "db_1     | database system is ready"
```

### 🎯 **URLs de Acesso Local**

#### Principais:
- **Interface Principal:** http://localhost/
- **Gantt Dinâmico:** http://localhost/gantt/
- **Admin Django:** http://localhost/admin/
- **Dashboard:** http://localhost/dashboard/

#### APIs de Desenvolvimento:
- **Recursos Gantt:** http://localhost/api/gantt/resources/
- **Eventos:** http://localhost/api/gantt/events/
- **Dados Formulários:** http://localhost/api/form-data/

### 📊 **Configuração Inicial Local**

#### **Método Recomendado - Script Automático**
```bash
# 1. Copiar script de dados iniciais para o container
docker cp init_data.py acr_gestao-web-1:/app/init_data.py

# 2. Executar script de inicialização automática
docker-compose -f docker-compose.prod.local.yml exec web python /app/init_data.py

# O script init_data.py cria automaticamente:
# ✅ Organização "ACR Gestão - Desenvolvimento Local"
# ✅ 3 Modalidades: Musculação, Cardio, Pilates (com cores e durações)
# ✅ 3 Recursos: Sala de Musculação, Sala Cardio, Estúdio Pilates
```

**Ficheiro `init_data.py` incluído no projeto:**
- Configura automaticamente Django
- Cria organização localhost
- Adiciona modalidades básicas com cores personalizadas
- Configura recursos/espaços para cada modalidade
- Pronto para usar imediatamente após o deploy

#### **Método Manual (Alternativo)**
Se preferir criar dados manualmente:
```bash
# Executar dentro do container Django
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py shell << 'EOF'
from core.models import Organization, Modality, Resource, Instructor

# Criar organizações de desenvolvimento
org_local, created = Organization.objects.get_or_create(
    domain='localhost',
    defaults={
        'name': 'ACR Local Development',
        'org_type': 'both',
        'gym_monthly_fee': 30.00,
        'wellness_monthly_fee': 45.00
    }
)
print(f"✅ Organização local: {'Created' if created else 'Updated'}")

# Modalidades básicas
modalities = [
    {'name': 'Musculação', 'entity_type': 'acr', 'color': '#dc3545'},
    {'name': 'Cardio', 'entity_type': 'acr', 'color': '#fd7e14'},
    {'name': 'Pilates', 'entity_type': 'proform', 'color': '#28a745'},
    {'name': 'Yoga', 'entity_type': 'proform', 'color': '#6f42c1'},
]

for mod_data in modalities:
    mod, created = Modality.objects.get_or_create(
        organization=org_local,
        name=mod_data['name'],
        defaults={
            'entity_type': mod_data['entity_type'],
            'color': mod_data['color'],
            'default_duration_minutes': 60,
            'max_capacity': 10
        }
    )
    print(f"✅ Modalidade {mod.name}: {'Created' if created else 'Updated'}")

# Recursos/Espaços básicos
resources = [
    {'name': 'Sala de Musculação', 'entity_type': 'acr', 'capacity': 25},
    {'name': 'Sala Cardio', 'entity_type': 'acr', 'capacity': 15},
    {'name': 'Estúdio Pilates', 'entity_type': 'proform', 'capacity': 10},
    {'name': 'Sala Polivalente', 'entity_type': 'both', 'capacity': 20},
]

for res_data in resources:
    res, created = Resource.objects.get_or_create(
        organization=org_local,
        name=res_data['name'],
        defaults={
            'entity_type': res_data['entity_type'],
            'capacity': res_data['capacity'],
            'is_available': True
        }
    )
    print(f"✅ Recurso {res.name}: {'Created' if created else 'Updated'}")

print("🎉 Setup local completo!")
EOF
```

#### 2. Criar instrutor de teste
```bash
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py shell << 'EOF'
from core.models import Organization, Instructor

org_local = Organization.objects.get(domain='localhost')

instructor, created = Instructor.objects.get_or_create(
    organization=org_local,
    email='admin@acr.local',
    defaults={
        'first_name': 'João',
        'last_name': 'Silva',
        'entity_affiliation': 'both',
        'specialties': 'Musculação, Pilates',
        'is_active': True
    }
)
print(f"✅ Instrutor teste: {'Created' if created else 'Updated'}")
EOF
```

### 🧪 **Testes do Sistema Local**

#### 1. Testar Gantt Dinâmico
1. Aceder a http://localhost/gantt/
2. Selecionar data atual
3. **Arrastar** no grid para criar aula
4. Configurar detalhes no modal
5. Verificar se aula aparece no grid

#### 2. Testar APIs
```bash
# Testar API de recursos
curl -s http://localhost/api/gantt/resources/ | python -m json.tool

# Testar API de eventos
curl -s http://localhost/api/gantt/events/ | python -m json.tool

# Deve retornar JSON válido com dados
```

### 🛠️ **Comandos Úteis para Desenvolvimento**

#### Gestão de Containers
```bash
# Ver status
docker-compose -f docker-compose.base-nginx.yml ps

# Ver logs em tempo real
docker-compose -f docker-compose.base-nginx.yml logs -f

# Reiniciar apenas Django
docker-compose -f docker-compose.base-nginx.yml restart web

# Parar tudo
docker-compose -f docker-compose.base-nginx.yml down

# Rebuild completo
docker-compose -f docker-compose.base-nginx.yml down
docker-compose -f docker-compose.base-nginx.yml up -d --build
```

#### Base de Dados
```bash
# Aceder ao shell Django
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py shell

# Aplicar migrações
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py migrate

# Criar superuser
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py createsuperuser

# Aceder diretamente ao PostgreSQL
docker-compose -f docker-compose.base-nginx.yml exec db psql -U acruser -d acrdb_local
```

### ⚠️ **Troubleshooting Local**

#### 1. Porta 80 ocupada
```bash
# Se der erro de porta ocupada, verificar:
sudo lsof -i :80

# Parar processo que usa porta 80 (ex: Apache)
sudo systemctl stop apache2  # Ubuntu/Debian
sudo brew services stop nginx  # macOS com Homebrew

# Ou alterar porta no docker-compose.base-nginx.yml:
# ports: - "8080:80"  # usar localhost:8080
```

#### 2. Problemas de permissões
```bash
# macOS/Linux - corrigir permissões
sudo chown -R $USER:$USER .
chmod +x deploy*.sh *.sh
```

#### 3. Limpar Docker se necessário
```bash
# Remover containers parados
docker container prune -f

# Remover volumes órfãos
docker volume prune -f

# Reset completo (CUIDADO - remove todos os dados)
docker-compose -f docker-compose.base-nginx.yml down -v
docker system prune -a -f
```

---

## 🏭 **DEPLOY PRODUÇÃO - Dois Hosts (App VM + Nginx CT)**

### 🧭 Arquitetura
- App VM (Debian) em 192.168.1.10: Docker Compose com Django (Gunicorn) + Postgres + Redis. Expõe a porta 8000 internamente.
- Nginx CT (Proxmox) em 192.168.1.20: termina TLS para acrsantatecla.duckdns.org e proformsc.duckdns.org e faz proxy para 192.168.1.10:8000.

### ✅ Pré-requisitos gerais
- DNS: ambos os domínios no DuckDNS devem apontar para o IP público do seu router/ISP.
- Router: encaminhar portas 80 e 443 para 192.168.1.20 (Nginx CT).

---

### 🖥️ Passo 1 — App VM (192.168.1.10)

1) Atualizar e instalar pacotes
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl git ufw
```

2) Instalar Docker + Compose plugin
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version && docker compose version
```

3) SSH key para GitHub e clonar por SSH
```bash
ssh-keygen -t ed25519 -C "acr-app@192.168.1.10" -N "" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub  # adicione em GitHub > Settings > SSH and GPG keys
ssh -T git@github.com      # deve mostrar mensagem de boas-vindas

git clone git@github.com:paulot41/acr_gestao.git
cd acr_gestao
```

4) Configurar ambiente de produção
```bash
cp .env.prod.example .env.prod
python3 - <<'PY'
import secrets
print('SECRET_KEY='+secrets.token_urlsafe(64))
PY
echo "Use o valor acima para SECRET_KEY e defina passwords fortes em .env.prod"
```

Edite `.env.prod` e garanta:
```bash
DEBUG=0
DJANGO_SETTINGS_MODULE=settings.production
ALLOWED_HOSTS=acrsantatecla.duckdns.org,proformsc.duckdns.org
DB_ENGINE=django.db.backends.postgresql
DB_HOST=db
DB_PORT=5432
REDIS_URL=redis://redis:6379/0
ACR_DOMAIN=acrsantatecla.duckdns.org
PROFORM_DOMAIN=proformsc.duckdns.org
```

5) Firewall (apenas Nginx CT pode aceder à app)
```bash
sudo ufw allow OpenSSH
sudo ufw allow from 192.168.1.20 to any port 8000 proto tcp
sudo ufw enable
```

6) Subir a stack da aplicação (ficheiro único de produção)
```bash
docker compose -f docker-compose.prod.full.yml up -d --build
docker compose -f docker-compose.prod.full.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.full.yml exec web python manage.py collectstatic --noinput
curl -f http://localhost:8000/health/
```

7) Criar superuser e organizações
```bash
docker compose -f docker-compose.prod.full.yml exec web python manage.py createsuperuser

docker compose -f docker-compose.prod.full.yml exec web python manage.py shell << 'EOF'
from core.models import Organization
Organization.objects.get_or_create(
    domain='acrsantatecla.duckdns.org',
    defaults={'name':'ACR Santa Tecla','org_type':'gym','gym_monthly_fee':30.0,'wellness_monthly_fee':0.0}
)
Organization.objects.get_or_create(
    domain='proformsc.duckdns.org',
    defaults={'name':'Proform Santa Clara','org_type':'wellness','gym_monthly_fee':0.0,'wellness_monthly_fee':45.0}
)
print('✅ Organizações configuradas')
EOF
```

---

### 🌐 Passo 2 — Nginx CT (192.168.1.20)

1) Instalar Docker e preparar pastas
```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl ufw
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER
newgrp docker
ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
mkdir -p ~/reverse-proxy/{certbot/conf,certbot/www}
cd ~/reverse-proxy
```

2) Configurar Nginx (usar template do repositório)
```bash
# Copie o template para este host
curl -o nginx-proxy.conf https://raw.githubusercontent.com/paulot41/acr_gestao/main/nginx-proxy.conf
# OU transfira manualmente o ficheiro nginx-proxy.conf deste repositório.
```

3) Iniciar Nginx (HTTP primeiro, para ACME webroot)
```bash
docker run -d --name nginx -p 80:80 -p 443:443 \
  -v "$(pwd)/nginx-proxy.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt:ro" \
  nginx:alpine
```

4) Obter certificados Let's Encrypt (SAN para ambos os domínios)
```bash
docker run --rm -it \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d acrsantatecla.duckdns.org -d proformsc.duckdns.org \
  --email you@example.com --agree-tos --no-eff-email

docker exec nginx nginx -s reload
```

5) Renovação automática (cron)
```bash
crontab -e
# Adicione:
0 3 * * * docker run --rm -v "$HOME/reverse-proxy/certbot/conf:/etc/letsencrypt" -v "$HOME/reverse-proxy/certbot/www:/var/www/certbot" certbot/certbot renew --webroot -w /var/www/certbot && docker exec nginx nginx -s reload
```

---

### 🔎 Validação final
```bash
# Do Nginx CT
curl -f http://192.168.1.10:8000/health/

# Público (DNS + router ok)
curl -I https://acrsantatecla.duckdns.org/health/
curl -I https://proformsc.duckdns.org/health/
```

### 🎯 URLs de Acesso em Produção
- https://acrsantatecla.duckdns.org
- https://proformsc.duckdns.org
- Admin: https://acrsantatecla.duckdns.org/admin/
- Gantt: https://acrsantatecla.duckdns.org/gantt/

---

## 🖥️ **Deploy em Servidor Linux (Sem Docker)**

Este modo usa **Gunicorn + systemd + Nginx**. Os ficheiros de exemplo estao em `deploy/`.

### 1. Preparar ambiente
```bash
# Diretoria do projeto
sudo mkdir -p /srv/acr_gestao
sudo chown $USER:www-data /srv/acr_gestao

# Virtualenv
python -m venv /srv/acr_gestao/.venv
source /srv/acr_gestao/.venv/bin/activate
pip install -r /srv/acr_gestao/requirements.txt
```

### 2. Configurar variaveis
```bash
cp deploy/env.example /srv/acr_gestao/.env
# Editar /srv/acr_gestao/.env com SECRET_KEY, DB_*, ALLOWED_HOSTS, etc.
```

### 3. Migrations e static
```bash
source /srv/acr_gestao/.venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
```

### 4. Gunicorn (systemd)
```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/acr_gestao.service
sudo systemctl daemon-reload
sudo systemctl enable --now acr_gestao
```

### 5. Nginx
```bash
sudo cp deploy/nginx_acr_gestao.conf /etc/nginx/sites-available/acr_gestao
sudo ln -s /etc/nginx/sites-available/acr_gestao /etc/nginx/sites-enabled/acr_gestao
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔍 **Diferenças entre Deploy Local vs Produção**

| Aspecto | Local (Docker Desktop) | Produção (Debian) |
|---------|----------------------|-------------------|
| **Domínio** | localhost | acrsantatecla.duckdns.org |
| **SSL** | ❌ HTTP simples | ✅ HTTPS automático |
| **Porta** | 80 (ou 8080) | 80/443 |
| **Base de Dados** | acrdb_local | acrdb |
| **Debug** | ✅ DEBUG=1 | ❌ DEBUG=0 |
| **Performance** | Desenvolvimento | Otimizada |
| **Logs** | Console | Ficheiros |
| **Backup** | Manual | Automático |

---

## 📦 **Scripts Disponíveis**

### Para Desenvolvimento Local:
- `deploy_nginx.sh --local` - Deploy local sem SSL
- `docker-compose -f docker-compose.base-nginx.yml up -d` - Deploy manual

### Para Produção:
- `deploy.sh` - Deploy produção completo
- `deploy_nginx.sh` - Deploy produção com Nginx + SSL
- `monitor.sh` - Monitorização de produção

---

## 🏆 **Sistema Pronto para Ambos os Ambientes!**

Com este guia, o sistema ACR Gestão está **100% funcional** tanto para:
- ✅ **Desenvolvimento local** no Docker Desktop
- ✅ **Produção** em servidor Debian
- ✅ **Gantt dinâmico** com drag & drop
- ✅ **Sistema de turmas** completo
- ✅ **Multi-tenancy** robusto
- ✅ **APIs otimizadas** para performance
