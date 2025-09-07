# 🚀 ACR Gestão - Deploy Local Docker Desktop

Sistema completo de gestão para ginásios ACR e Proform com deploy automatizado para Docker Desktop.

## ⚡ Início Rápido (2 minutos)

```bash
# 1. Validar sistema
make validate

# 2. Deploy automático
make quick-start
```

**URLs após deploy:**
- 🌐 **Principal:** http://localhost:8080/
- 🎯 **Gantt:** http://localhost:8080/gantt/
- ⚙️ **Admin:** http://localhost:8080/admin/ (admin/admin123)

## 📋 Comandos Disponíveis

### Deploy Inicial
```bash
./quick_start.sh          # Deploy automático completo
./deploy_local.sh          # Deploy interativo com opções
make quick-start           # Via Makefile
```

### Gestão Diária
```bash
make status               # Ver status dos containers
make logs                 # Ver logs
make restart-web         # Reiniciar apenas Django
make shell               # Shell Django
make urls                # Mostrar URLs
```

### Manutenção
```bash
make backup              # Backup base de dados
make clean               # Limpar sistema (apaga dados!)
make reset               # Reset completo
```

## 🎯 Funcionalidades Incluídas

✅ **Gantt Dinâmico** - Drag & drop para criar aulas  
✅ **Sistema Multi-tenant** - ACR + Proform  
✅ **Gestão de Turmas** - Grupos de clientes  
✅ **APIs Otimizadas** - Performance máxima  
✅ **Interface Responsiva** - Mobile-ready  
✅ **Dados de Exemplo** - Modalidades e instrutores  

## 📦 Estrutura Criada

```
acr_gestao/
├── 🚀 Scripts de Deploy
│   ├── quick_start.sh           # Deploy automático
│   ├── deploy_local.sh          # Deploy interativo
│   └── validate_setup.sh        # Validação sistema
├── 🐳 Docker
│   ├── docker-compose.base-nginx.yml
│   ├── Dockerfile
│   └── nginx.conf
├── ⚙️ Configuração
│   ├── .env.local              # Configuração desenvolvimento
│   └── init_data.py            # Dados iniciais
└── 🛠️ Utilitários
    └── Makefile                # Comandos simplificados
```

## 🔧 Resolução de Problemas

### Porta 8080 ocupada
```bash
# Verificar o que usa a porta
sudo lsof -i :8080

# Ou alterar porta no docker-compose
# ports: - "8081:80"  # usar localhost:8081
```

### Reset completo
```bash
make clean    # Limpar tudo
make reset    # Limpar + deploy inicial
```

### Ver logs detalhados
```bash
make logs-follow  # Logs em tempo real
docker-compose -f docker-compose.base-nginx.yml logs web  # Apenas Django
```

## 📊 Dados Incluídos

**Organização:** ACR Gestão - Desenvolvimento Local

**Modalidades:**
- 🔴 Musculação (ACR) - 60min
- 🟠 Cardio (ACR) - 45min  
- 🟢 Pilates (Proform) - 60min
- 🟣 Yoga (Proform) - 75min

**Espaços:**
- Sala de Musculação (25 pessoas)
- Sala Cardio (15 pessoas)
- Estúdio Pilates (10 pessoas)
- Sala Polivalente (20 pessoas)

**Instrutores:**
- João Silva (ACR) - Musculação
- Maria Santos (Proform) - Pilates/Yoga  
- Carlos Mendes (Ambos) - Personal Training

## 🎉 Sistema Pronto!

Após o deploy, tem acesso imediato a:
- ✅ Interface web funcional
- ✅ Gantt dinâmico operacional
- ✅ Base de dados com dados exemplo
- ✅ Sistema multi-tenant configurado
- ✅ APIs todas funcionais

**Credenciais:** admin / admin123
