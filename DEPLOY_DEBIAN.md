# 🚀 Guia de Deploy - VM Debian/Proxmox

## 📋 Pré-requisitos na VM Debian

### 1. Atualizar o sistema
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Instalar Docker
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
```

### 3. Instalar Docker Compose (standalone)
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 4. Instalar Git
```bash
sudo apt install -y git
```

## 🔄 Deploy do Projeto

### 1. Clonar o repositório
```bash
cd /home/$USER
git clone https://github.com/paulot41/acr_gestao.git
cd acr_gestao
```

### 2. Configurar ambiente de produção
```bash
# Copiar arquivo de configuração
cp .env.prod.example .env.prod

# Gerar SECRET_KEY segura
python3 -c 'import secrets; print("SECRET_KEY=" + secrets.token_urlsafe(50))' >> temp_key.txt
echo "✅ SECRET_KEY gerada. Copie o valor de temp_key.txt para .env.prod"
cat temp_key.txt
```

### 3. Editar configurações
```bash
nano .env.prod
```

**Configurar as seguintes variáveis:**
```bash
# Usar a SECRET_KEY gerada acima
SECRET_KEY=sua_chave_secreta_aqui

DEBUG=0
ALLOWED_HOSTS=acrsantatecla.duckdns.org,proformsc.duckdns.org

# Base de dados
DB_ENGINE=django.db.backends.postgresql
DB_NAME=acrdb
DB_USER=acruser
DB_PASSWORD=senha_super_segura_aqui
DB_HOST=db
DB_PORT=5432

# PostgreSQL (container)
POSTGRES_DB=acrdb
POSTGRES_USER=acruser
POSTGRES_PASSWORD=senha_super_segura_aqui

# Superusuário (opcional)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@exemplo.com
DJANGO_SUPERUSER_PASSWORD=senha_admin_aqui
```

### 4. Validar configuração
```bash
chmod +x validate.sh deploy.sh monitor.sh
./validate.sh
```

### 5. Deploy automático
```bash
./deploy.sh
```

### 6. Configuração pós-deploy
```bash
# Criar superusuário
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py setup_production --create-superuser

# Criar organizações
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py setup_production --create-org acrsantatecla.duckdns.org --org-name "ACR Santa Tecla"

docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py setup_production --create-org proformsc.duckdns.org --org-name "Proform SC"
```

## 🔧 Configuração de Firewall (Opcional mas Recomendado)

### UFW (Ubuntu/Debian)
```bash
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 🔍 Verificação e Monitoramento

### 1. Verificar status
```bash
./monitor.sh
```

### 2. Ver logs em tempo real
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### 3. Verificar containers
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

### 4. Testar conectividade
```bash
curl -I https://acrsantatecla.duckdns.org
curl -I https://proformsc.duckdns.org
```

## 📦 Comandos Úteis

### Parar serviços
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### Reiniciar serviços
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart
```

### Backup manual
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec db pg_dump -U acruser acrdb | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Ver utilização de recursos
```bash
docker stats
```

### Limpar Docker (se necessário)
```bash
docker system prune -a --volumes
```

## ⚠️ Resolução de Problemas

### Se o deploy falhar:
1. Verificar logs: `docker-compose logs`
2. Verificar configuração: `./validate.sh`
3. Verificar conectividade de rede
4. Verificar se as portas 80/443 estão livres

### Se os domínios não resolverem:
1. Verificar DNS no DuckDNS
2. Verificar se o IP da VM está correto
3. Aguardar propagação DNS (pode demorar até 10 minutos)

### Problemas de SSL/HTTPS:
- O Caddy gera certificados automaticamente
- Pode demorar alguns minutos na primeira vez
- Verificar logs do Caddy: `docker-compose logs caddy`

## 🎯 URLs de Acesso

Após o deploy bem-sucedido:
- **ACR Santa Tecla:** https://acrsantatecla.duckdns.org
- **Proform SC:** https://proformsc.duckdns.org
- **Admin Django:** https://acrsantatecla.duckdns.org/admin/

## 📱 Atualizações Futuras

```bash
cd /home/$USER/acr_gestao
git pull origin main
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
