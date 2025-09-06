# 🚀 Guia de Deploy - Produção & Desenvolvimento

## 📋 **TIPOS DE DEPLOY DISPONÍVEIS**

Este projeto suporta **dois tipos de deploy**:
- 🏭 **PRODUÇÃO (Debian/Ubuntu)** - Deploy completo com SSL e domínios
- 💻 **DESENVOLVIMENTO LOCAL (Docker Desktop)** - Testes e desenvolvimento

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

#### 1. Criar dados básicos de desenvolvimento
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

## 🏭 **DEPLOY PRODUÇÃO - VM Debian/Proxmox**

### ✨ **NOVIDADES DA VERSÃO ATUAL**
- 🎯 **Gantt Dinâmico** com drag & drop para criação de aulas
- 👥 **Sistema de Turmas** completo integrado
- 🔄 **APIs otimizadas** para performance máxima
- 📱 **Interface responsiva** moderna
- ⚡ **Validações em tempo real** de conflitos
- 🎨 **Personalização por modalidade** (cores, durações)

### 📋 Pré-requisitos na VM Debian

#### 1. Atualizar o sistema
```bash
sudo apt update && sudo apt upgrade -y
```

#### 2. Instalar Docker
```bash
# Remover versões antigas do Docker
sudo apt remove docker docker-engine docker.io containerd runc

# Instalar dependências
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Adicionar chave GPG oficial do Docker
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Adicionar repositório Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER

# Reiniciar sessão para aplicar mudanças de grupo
echo "⚠️  IMPORTANTE: Fazer logout/login para aplicar mudanças do grupo docker"
```

#### 3. Instalar Docker Compose (standalone)
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalação
docker-compose --version
```

#### 4. Instalar Git e utilitários
```bash
sudo apt install -y git curl htop nano vim
```

### 🔄 Deploy do Projeto em Produção

#### 1. Clonar o repositório
```bash
cd /home/$USER
git clone https://github.com/paulot41/acr_gestao.git
cd acr_gestao

# Verificar se todos os ficheiros estão presentes
ls -la
echo "✅ Verificar se existem: docker-compose.yml, Dockerfile, deploy.sh"
```

#### 2. Configurar ambiente de produção
```bash
# Copiar arquivo de configuração
cp .env.prod.example .env.prod

# Gerar SECRET_KEY segura
python3 -c 'import secrets; print("SECRET_KEY=" + secrets.token_urlsafe(50))' >> temp_key.txt
echo "✅ SECRET_KEY gerada. Copie o valor de temp_key.txt para .env.prod"
cat temp_key.txt

# Limpar arquivo temporário após uso
rm temp_key.txt
```

#### 3. Editar configurações de produção
```bash
nano .env.prod
```

**Configurar as seguintes variáveis:**
```bash
# OBRIGATÓRIO: Usar a SECRET_KEY gerada acima
SECRET_KEY=sua_chave_secreta_super_longa_aqui

# Produção
DEBUG=0
ALLOWED_HOSTS=acrsantatecla.duckdns.org,proformsc.duckdns.org,localhost,127.0.0.1

# Base de dados PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_NAME=acrdb
DB_USER=acruser
DB_PASSWORD=senha_super_segura_postgresql_aqui
DB_HOST=db
DB_PORT=5432

# PostgreSQL (container)
POSTGRES_DB=acrdb
POSTGRES_USER=acruser
POSTGRES_PASSWORD=senha_super_segura_postgresql_aqui

# Superusuário Django (opcional mas recomendado)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@acr.pt
DJANGO_SUPERUSER_PASSWORD=senha_admin_muito_segura_aqui

# URLs dos domínios
ACR_DOMAIN=acrsantatecla.duckdns.org
PROFORM_DOMAIN=proformsc.duckdns.org

# Performance
REDIS_URL=redis://redis:6379/0
```

#### 4. Deploy automático em produção
```bash
# Tornar scripts executáveis
chmod +x deploy.sh deploy_nginx.sh monitor.sh

# Validar configuração
./validate_compose.sh

# Deploy completo com SSL
./deploy_nginx.sh

# Ou deploy manual para produção:
docker-compose -f docker-compose.base-nginx.yml -f docker-compose.prod.yml up -d --build
```

#### 5. Configuração pós-deploy produção
```bash
# Criar superusuário (se não configurado no .env.prod)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Criar organizações para os domínios
docker-compose -f docker-compose.base-nginx.yml -f docker-compose.prod.yml exec web python manage.py shell << 'EOF'
from core.models import Organization
# ACR Santa Tecla
acr, created = Organization.objects.get_or_create(
    domain='acrsantatecla.duckdns.org',
    defaults={
        'name': 'ACR Santa Tecla',
        'org_type': 'gym',
        'gym_monthly_fee': 30.00,
        'wellness_monthly_fee': 0.00
    }
)
print(f"ACR: {'Created' if created else 'Updated'} - {acr}")

# Proform SC
proform, created = Organization.objects.get_or_create(
    domain='proformsc.duckdns.org',
    defaults={
        'name': 'Proform Santa Clara',
        'org_type': 'wellness',
        'gym_monthly_fee': 0.00,
        'wellness_monthly_fee': 45.00
    }
)
print(f"Proform: {'Created' if created else 'Updated'} - {proform}")
EOF

# Criar dados de exemplo (opcional)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py shell << 'EOF'
from core.models import Organization, Modality, Resource, Instructor

# Para cada organização, criar modalidades e recursos básicos
for org in Organization.objects.all():
    print(f"Setting up {org.name}...")
    
    # Modalidades básicas
    if org.org_type in ['gym', 'both']:
        Modality.objects.get_or_create(
            organization=org, name='Musculação',
            defaults={'entity_type': 'acr', 'color': '#dc3545', 'max_capacity': 20}
        )
        Resource.objects.get_or_create(
            organization=org, name='Sala de Musculação',
            defaults={'entity_type': 'acr', 'capacity': 25}
        )
    
    if org.org_type in ['wellness', 'both']:
        Modality.objects.get_or_create(
            organization=org, name='Pilates',
            defaults={'entity_type': 'proform', 'color': '#28a745', 'max_capacity': 8}
        )
        Resource.objects.get_or_create(
            organization=org, name='Estúdio Pilates',
            defaults={'entity_type': 'proform', 'capacity': 10}
        )
    
    print(f"✅ {org.name} configured successfully")
EOF
```

### 🎯 URLs de Acesso em Produção

#### Principais:
- **ACR Santa Tecla:** https://acrsantatecla.duckdns.org
- **Proform SC:** https://proformsc.duckdns.org

#### Funcionalidades:
- **Gantt Dinâmico:** https://acrsantatecla.duckdns.org/gantt/
- **Admin Django:** https://acrsantatecla.duckdns.org/admin/
- **Dashboard:** https://acrsantatecla.duckdns.org/dashboard/

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
