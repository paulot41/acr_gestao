# ACR GESTÃO - GUIA COMPLETO DO PROJETO

## 📖 VISÃO GERAL DO PROJETO

O **ACR Gestão** é uma aplicação Django para gestão completa de ginásios, desenvolvida como evolução do sistema GIG. Atualmente funciona como API REST pura, mas será expandida para incluir interface web completa com funcionalidades avançadas.

### 🎯 OBJETIVOS PRINCIPAIS
- Gestão completa de clientes e memberships
- Sistema Gantt para marcação de espaços por instrutores
- Controlo financeiro com pagamentos e relatórios
- Integração com Google Calendar e Google Drive
- Interface web intuitiva e responsiva

---

## 🏗️ ARQUITETURA ATUAL

### **Framework & Tecnologias**
- **Backend**: Django + Django Rest Framework
- **Base de Dados**: SQLite (desenvolvimento) / PostgreSQL (produção)
- **Deploy**: Docker + Nginx
- **Multi-tenancy**: Sistema baseado em domínios
- **Multi-entidade**: ACR + Proform com faturação separada

### **Sistema Multi-Entidade (ACR + Proform)**
O sistema suporta duas entidades distintas na mesma plataforma:

#### **🏋️ ACR (Ginásio)**
- **Tipo**: Ginásio tradicional
- **Modalidades**: Musculação, CrossFit, Cardio
- **Espaços**: Ginásio, Pavilhão
- **Faturação**: Mensalidades de ginásio
- **URL**: `/acr/` ou subdomínio acr.dominio.com

#### **🧘 Proform (Pilates/Wellness)**  
- **Tipo**: Estúdio de Pilates e Wellness
- **Modalidades**: Pilates, Yoga, Stretching
- **Espaços**: Sala de Pilates, Sala de Yoga
- **Faturação**: Mensalidades de pilates/wellness
- **URL**: `/proform/` ou subdomínio proform.dominio.com

#### **👥 Utilizadores Multi-Entidade**
- **Clientes**: Podem estar inscritos numa ou ambas entidades
- **Instrutores**: Podem trabalhar para uma ou ambas entidades  
- **Faturação Separada**: Cada entidade tem a sua própria estrutura de preços
- **Comissões Configuráveis**: % para instrutor vs. % para entidade

### **Modelos Existentes**
- `Organization` - Entidade tenant (multi-tenant) **- Expandido para multi-entidade**
- `Person` - Clientes/atletas (expandido com foto, status, dados completos)
- `Instructor` - Personal Trainers e instrutores (novo) **- Suporta multi-entidade**
- `Modality` - Modalidades de exercício com cores (novo)
- `Membership` - Subscrições/memberships **- Expandido para multi-entidade**
- `Product` - Produtos/serviços faturáveis
- `Price` - Preços com validade temporal
- `Resource` - Recursos bookáveis (salas/espaços)
- `ClassTemplate` - Templates para aulas recorrentes
- `Event` - Eventos/aulas agendadas
- `Booking` - Reservas de clientes para eventos
- `Payment` - Registo de pagamentos (novo) **- Faturação separada por entidade**
- `InstructorCommission` - Comissões de instrutores (novo)

### **APIs Existentes**
- PersonViewSet - CRUD de clientes
- MembershipViewSet - CRUD de memberships
- ProductViewSet - CRUD de produtos
- EventViewSet - CRUD de eventos com booking
- BookingViewSet - CRUD de reservas

### **Interface Web Implementada (Fase 1)**
- Dashboard interativo com KPIs e estatísticas
- Sistema Gantt completo com FullCalendar.js
- Gestão de clientes, instrutores e modalidades
- Autenticação web com página de login moderna
- Templates responsivos com Bootstrap 5

---

## 🎯 FUNCIONALIDADES ESPECÍFICAS SOLICITADAS

### 📅 **SISTEMA GANTT PARA ESPAÇOS (✅ IMPLEMENTADO)**
**Espaços disponíveis:**
- Ginásio (azul - capacidade 20)
- Sala de Pilates (verde - capacidade 15)
- Pavilhão (amarelo - capacidade 30)

**Funcionalidades implementadas:**
- ✅ Interface Gantt interativa para marcação
- ✅ Visualização de ocupação por espaço/instrutor
- ✅ Drag & drop para marcações rápidas
- ✅ Cores diferentes por modalidade/instrutor
- ✅ Detecção visual de conflitos
- ✅ Marcações recorrentes (estrutura preparada)
- ✅ Filtros por espaço, instrutor e modalidade

### 🏋️ **GESTÃO DE MODALIDADES (✅ IMPLEMENTADO)**
- ✅ Adição manual de modalidades
- ✅ Associação modalidade-instrutor-espaço
- ✅ Definição de capacidade máxima
- ✅ Duração típica por modalidade
- ✅ Cores personalizadas para visualização Gantt

### 📱 **INTEGRAÇÃO GOOGLE CALENDAR (🔄 FASE 2)**
- 🔄 Exportação individual das marcações de cada instrutor
- 🔄 Sincronização bidirecional
- 🔄 Notificações automáticas de mudanças
- 🔄 Partilha de calendários entre equipa

### ☁️ **SISTEMA DE BACKUPS GOOGLE DRIVE (🔄 FASE 2)**
- 🔄 Backup automático da base de dados (diário/semanal)
- 🔄 Exportação Excel completa de clientes
- 🔄 Relatórios automáticos em Excel/PDF
- 🔄 Versionamento de backups
- 🔄 Restore automático
- 🔄 Notificações de backup (sucesso/erro)

---

## 📋 ROADMAP DE DESENVOLVIMENTO - TRACKING DE PROGRESSO

### **✅ PASSO 1 - PROBLEMA "EMPTY COMPOSE FILE" (CONCLUÍDO)** ✓
**Estado: 100% Resolvido - CONCLUÍDO em 04/09/2025**

#### ✅ Resolução Imediata
- ✅ Erro "empty compose file" identificado e corrigido
- ✅ Arquivo docker-compose.base-nginx.yml restaurado via git
- ✅ Servidor de produção restaurado ao funcionamento

#### ✅ Medidas Preventivas Implementadas
- ✅ Script `validate_compose.sh` criado
- ✅ Script `recover.sh` para recuperação automática
- ✅ `deploy_nginx.sh` atualizado com validações
- ✅ `test_system.sh` para verificação do sistema
- ✅ Documentação completa em `TROUBLESHOOTING.md`

#### ✅ Scripts de Prevenção
- ✅ Validação automática antes de cada deploy
- ✅ Backup automático de arquivos críticos
- ✅ Recuperação automatizada em caso de problemas
- ✅ Logs detalhados para troubleshooting

**STATUS: ✅ PASSO 1 CONCLUÍDO - Problema resolvido com medidas preventivas**

---

### **🚀 PASSO 2 - DJANGO ADMIN UNIFICADO (EM CURSO)** 
**Estado: 90% Implementado - DEPLOY EM ANDAMENTO**

#### ✅ Implementação Concluída (IDE Local)
- ✅ **Django Admin Site customizado** (`ACRAdminSite`)
- ✅ **Dashboard integrado** na página inicial do admin
- ✅ **Templates modernizados** (base_site.html, index.html)
- ✅ **URLs simplificadas** (eliminadas interfaces redundantes)
- ✅ **Estatísticas detalhadas** por entidade (ACR/Proform)
- ✅ **Interface responsiva** com Bootstrap 5 e Bootstrap Icons
- ✅ **Auto-refresh** automático a cada 5 minutos
- ✅ **Badges coloridos** para identificar entidades
- ✅ **Ações rápidas** para criar registos
- ✅ **Correção ImportError** - admin_site adicionado

#### ✅ Validação Local Concluída
- ✅ **Django iniciado sem erros** no IDE local
- ✅ **Admin disponível** em http://127.0.0.1:8000/admin/
- ✅ **Login funcional** (admin/admin123)
- ✅ **Organização de teste** criada ("ACR Gestão - Local")
- ✅ **Todas as funcionalidades** testadas e operacionais
- ✅ **Código commitado** e pushed para repositório

#### 🔄 Deploy no Servidor (EM ANDAMENTO)
- ✅ **Código preparado** para produção
- ✅ **Scripts de deploy** atualizados
- 🔄 **EXECUTAR AGORA**: Deploy no servidor /srv/acr_gestao

#### 📋 Comandos para Deploy do Passo 2:
```bash
# No servidor de produção:
cd /srv/acr_gestao
git pull origin main
grep -n "admin_site" core/admin.py  # Verificar correção
./deploy_nginx.sh
```

#### 🎯 Resultado Esperado do Passo 2:
- **URL única:** https://seu-dominio.com/admin/
- **Interface unificada** com dashboard integrado
- **Eliminação de 3 interfaces** → **1 interface moderna**
- **Performance melhorada** e manutenção simplificada

**STATUS: 🚀 PASSO 2 - 90% CONCLUÍDO - Pronto para deploy final**

---

### **⏳ FASE 1 - INTERFACE WEB + GANTT (PRÓXIMA APÓS PASSO 2)**
**Estado: Aguardando conclusão do Passo 2**

#### Templates e Interface Base
- [ ] Sistema de templates Django completo
- [ ] Template base (base.html) com Bootstrap 5
- [ ] Navbar com navegação principal
- [ ] Footer e estrutura responsiva
- [ ] Sistema de mensagens/alerts

#### Sistema de Autenticação Web
- [ ] Páginas de login/logout com design moderno
- [ ] Gestão de utilizadores
- [ ] Middleware de autenticação web
- [ ] Perfis diferentes (admin, rececionista, instrutor)

#### CRUD Web Completo
- [ ] Listagem de clientes com filtros e paginação
- [ ] Formulários para criar/editar clientes
- [ ] Páginas de detalhes completas
- [ ] Confirmações de eliminação
- [ ] CRUD de modalidades com cores
- [ ] CRUD de instrutores

#### Interface Gantt
- [ ] FullCalendar.js implementado
- [ ] Vista de ocupação dos 3 espaços
- [ ] Drag & drop para marcações
- [ ] Cores por modalidade/instrutor
- [ ] Filtros por espaço/instrutor/modalidade
- [ ] Detecção e aviso de conflitos

#### Dashboard Principal
- [ ] KPIs principais (clientes ativos, ocupação, receita)
- [ ] Gráficos de ocupação por espaço
- [ ] Próximas aulas do dia
- [ ] Alertas importantes
- [ ] Ações rápidas para criação de registos

---

### **🔄 FASE 2 - INTEGRAÇÕES E BACKUPS (FUTURA)**
**Prioridade: ALTA - Após Fase 1**

#### Integração Google Calendar
- [ ] Configurar Google Calendar API
- [ ] Exportação individual por instrutor
- [ ] Sincronização bidirecional
- [ ] ICS export para outros calendários
- [ ] Notificações de mudanças

#### Sistema de Backups Google Drive
- [ ] Configurar Google Drive API
- [ ] Backup automático da BD
- [ ] Exportação Excel de clientes (openpyxl)
- [ ] Agendamento de backups (Celery + Redis)
- [ ] Interface de restore
- [ ] Logs e notificações de backup

#### Gestão Financeira Básica
- [ ] Expandir modelo Payment
- [ ] Interface web para pagamentos
- [ ] Métodos de pagamento (dinheiro, cartão, transferência)
- [ ] Relatórios financeiros básicos
- [ ] Alertas de pagamentos em atraso

---

## 📊 TRACKING DE PROGRESSO ATUAL

### **Progresso Geral do Projeto:**
- ✅ **PASSO 1 - Correções Críticas:** 100% CONCLUÍDO ✓
- 🚀 **PASSO 2 - Admin Unificado:** 90% - Deploy em andamento
- ⏳ **FASE 1 - Interface Web:** 0% - Aguardando Passo 2
- ⏳ **FASE 2 - Integrações:** 0% - Futuro

### **Ação Imediata Necessária:**
🔄 **DEPLOY DO PASSO 2 NO SERVIDOR DE PRODUÇÃO**

**Comandos para executar AGORA:**
```bash
cd /srv/acr_gestao
git pull origin main
./deploy_nginx.sh
```

**Data de Início Passo 2:** 04/09/2025
**Meta de Conclusão Passo 2:** 04/09/2025 (hoje)

---

## 🚀 DEPLOY E INFRAESTRUTURA

### **📦 PROCESSO DE DEPLOY PARA PRODUÇÃO**

#### 1. **Pré-requisitos no Servidor**
- ✅ Docker e Docker Compose instalados
- ✅ Nginx configurado
- ✅ SSL/TLS configurado
- ✅ Domínio configurado
- ✅ PostgreSQL em container
- ✅ Todas as dependências instaladas

#### 2. **Localização do Projeto na VM**
```bash
# Caminho do projeto no servidor de produção:
/srv/acr_gestao
```

#### 3. **Deploy da Fase 1 - Procedimento Completo**

```bash
# No servidor de produção (VM):

# 1. Navegar para o diretório do projeto
cd /srv/acr_gestao

# 2. Executar o script de deploy automatizado da Fase 1
./deploy_fase1.sh

# OU executar os passos manualmente:

# 2.1. Fazer pull das alterações
git fetch origin main
git merge origin/main

# 2.2. Validar integridade dos arquivos
./validate_compose.sh

# 2.3. Fazer backup atual (se existir)
./backup_current_system.sh  # (se existir)

# 2.4. Deploy com validação automática
./deploy_nginx.sh

# 2.5. Executar migrações
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py migrate

# 2.6. Criar dados de exemplo (primeira vez)
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py create_sample_data

# 2.7. Coletar arquivos estáticos
docker-compose -f docker-compose.base-nginx.yml exec web python manage.py collectstatic --noinput

# 2.8. Testar sistema
./test_system.sh
```

#### 4. **Verificações Pós-Deploy**

```bash
# No diretório /srv/acr_gestao:

# Verificar status dos containers
docker-compose -f docker-compose.base-nginx.yml ps

# Verificar logs da aplicação
docker-compose -f docker-compose.base-nginx.yml logs web

# Verificar se a interface web está funcional
curl -I https://seudominio.com/
curl -I https://seudominio.com/api/

# Testar login na interface web
# URL: https://seudominio.com/login/
# Credenciais: admin / admin123
```

#### 5. **Estrutura de URLs Atualizada**

**Interface Web:**
- `/` - Dashboard principal
- `/login/` - Página de login
- `/clientes/` - Gestão de clientes
- `/instrutores/` - Gestão de instrutores  
- `/modalidades/` - Gestão de modalidades
- `/gantt/` - Sistema Gantt para espaços
- `/aulas/` - Gestão de eventos/aulas

**API REST (mantida):**
- `/api/` - Root da API
- `/api/people/` - CRUD de clientes
- `/api/events/` - CRUD de eventos
- `/api/bookings/` - CRUD de reservas
- `/health/` - Health check
- `/admin/` - Interface administrativa Django

#### 6. **Configurações Específicas da Fase 1**

**Novos Middlewares:**
- Sistema de autenticação web integrado
- Multi-tenancy mantido e funcional

**Novos Templates:**
- Sistema completo de templates responsivos
- Bootstrap 5 integrado
- FullCalendar.js para interface Gantt

**Novos Modelos de Dados:**
- Instructor (instrutores)
- Modality (modalidades com cores)
- Payment (pagamentos - estrutura básica)
- Person expandido (foto, status, dados completos)

**Arquivos Estáticos:**
- `/static/css/custom.css` - Estilos personalizados
- Templates em `/core/templates/`
- Imagens de clientes em `/media/clients/`
- Imagens de instrutores em `/media/instructors/`

#### 7. **Script de Deploy Automatizado**

O projeto inclui um script `deploy_fase1.sh` que automatiza todo o processo:

```bash
# No servidor de produção:
cd /srv/acr_gestao
./deploy_fase1.sh
```

**O script executa automaticamente:**
1. Pull das alterações do GitHub
2. Validação de arquivos Docker Compose
3. Deploy com `./deploy_nginx.sh`
4. Migrações da base de dados
5. Criação de dados de exemplo
6. Coleta de arquivos estáticos
7. Testes do sistema
8. Relatório final com URLs e credenciais
