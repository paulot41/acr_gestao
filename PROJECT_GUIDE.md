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

### **✅ PASSO 2 - DJANGO ADMIN UNIFICADO (CONCLUÍDO)** ✓
**Estado: 100% Implementado - CONCLUÍDO em 04/09/2025**

#### ✅ Implementação Concluída
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

#### ✅ Deploy em Produção Concluído
- ✅ **Script de deploy** `deploy_passo2_admin_unificado.sh` executado
- ✅ **Django Admin Unificado** funcional em produção
- ✅ **Interface única** substituindo 3 interfaces antigas
- ✅ **URL de produção:** https://seu-dominio.com/admin/
- ✅ **Performance otimizada** e manutenção simplificada

**STATUS: ✅ PASSO 2 CONCLUÍDO - Django Admin Unificado em produção**

---

### **🚀 FASE 1 - INTERFACE WEB + GANTT (EM ANDAMENTO)** 
**Estado: 0% - INICIANDO EM 04/09/2025**

#### 🎯 Objetivos da Fase 1
Desenvolver interface web completa para utilizadores finais (clientes, rececionistas, instrutores) com:

#### 📋 Templates e Interface Base (PRÓXIMO)
- [ ] **Sistema de templates Django** completo e responsivo
- [ ] **Template base** (base.html) com Bootstrap 5 atualizado
- [ ] **Navbar** com navegação principal e multi-entidade
- [ ] **Footer** e estrutura responsiva otimizada
- [ ] **Sistema de mensagens/alerts** para feedback do utilizador

#### 🔐 Sistema de Autenticação Web (PRÓXIMO)
- [ ] **Páginas de login/logout** com design moderno ACR/Proform
- [ ] **Gestão de utilizadores** com perfis diferenciados
- [ ] **Middleware de autenticação** web integrado
- [ ] **Perfis de acesso:** admin, rececionista, instrutor, cliente

#### 📝 CRUD Web Completo (PRIORITÁRIO)
- [ ] **Listagem de clientes** com filtros avançados e paginação
- [ ] **Formulários** para criar/editar clientes com validação
- [ ] **Páginas de detalhes** completas com histórico
- [ ] **Confirmações de eliminação** e operações em lote
- [ ] **CRUD de modalidades** com cores e configurações
- [ ] **CRUD de instrutores** com especialidades e comissões

#### 📅 Interface Gantt (CORE FEATURE)
- [ ] **FullCalendar.js** implementado e configurado
- [ ] **Vista de ocupação** dos 3 espaços (Ginásio, Pilates, Pavilhão)
- [ ] **Drag & drop** para marcações rápidas e intuitivas
- [ ] **Cores diferenciadas** por modalidade/instrutor/entidade
- [ ] **Filtros dinâmicos** por espaço/instrutor/modalidade/data
- [ ] **Detecção e aviso** de conflitos de horários
- [ ] **Reserva de espaços** pelos instrutores
- [ ] **Visualização de ocupação** em tempo real

#### 📊 Dashboard Principal (ESSENCIAL)
- [ ] **KPIs principais** (clientes ativos, ocupação semanal, receita)
- [ ] **Gráficos de ocupação** por espaço e modalidade
- [ ] **Próximas aulas do dia** com detalhes e ocupação
- [ ] **Alertas importantes** (conflitos, atrasos, pagamentos)
- [ ] **Ações rápidas** para criação de registos
- [ ] **Notificações** em tempo real

**STATUS: 🚀 FASE 1 - INICIANDO - Interface Web + Sistema Gantt**
