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

### **🚀 FASE 1 - INTERFACE WEB + GANTT (100% CONCLUÍDA)** ✅
**Estado: 100% CONCLUÍDA - Finalizada em 04/09/2025**

#### 🎯 Objetivos da Fase 1
Desenvolver interface web completa para utilizadores finais (clientes, rececionistas, instrutores) com:

#### ✅ Templates e Interface Base (100% CONCLUÍDO)
- ✅ **Sistema de templates Django** completo e responsivo
- ✅ **Template base** (base.html) com Bootstrap 5 atualizado
- ✅ **Navbar** com navegação principal e multi-entidade
- ✅ **Footer** e estrutura responsiva otimizada
- ✅ **Sistema de mensagens/alerts** para feedback do utilizador
- ✅ **Dashboard Principal** moderno com KPIs e estatísticas

#### ✅ CRUD Web Completo (100% CONCLUÍDO)
- ✅ **Sistema CRUD de Clientes** completo:
  - ✅ Listagem com filtros avançados e paginação
  - ✅ Formulário moderno para criar/editar com validação
  - ✅ Página de detalhes completa com histórico
  - ✅ Upload de fotos e campos personalizados
- ✅ **Sistema CRUD de Instrutores** completo:
  - ✅ Listagem em grid/tabela com especialidades
  - ✅ Página de detalhes com próximas aulas e comissões
  - ✅ Formulário avançado com multi-entidade e modalidades
  - ✅ Gestão de fotos e configurações profissionais
- ✅ **Sistema CRUD de Modalidades** funcional
- ✅ **Sistema CRUD de Aulas/Eventos** avançado:
  - ✅ Listagem com filtros por período, modalidade, instrutor
  - ✅ Estatísticas em tempo real (hoje, próximas, total)
  - ✅ Vista detalhada com ocupação e estado das aulas
- ✅ **URLs completas** configuradas para todos os CRUDs
- ✅ **Views otimizadas** com filtros, paginação e relacionamentos

#### ✅ Interface Gantt (100% CONCLUÍDO)
- ✅ **FullCalendar.js** implementado e configurado
- ✅ **Vista de ocupação** dos 3 espaços (Ginásio, Pilates, Pavilhão)
- ✅ **Sistema Gantt** completo integrado ao dashboard
- ✅ **API JSON** para eventos do calendário

#### ✅ Sistema de Autenticação Web (100% CONCLUÍDO)
- ✅ **Páginas de login/logout** modernas com design ACR/Proform
- ✅ **Seletor de entidade** integrado no login (ACR Ginásio vs Proform Wellness)
- ✅ **Views personalizadas** de autenticação com funcionalidades avançadas
- ✅ **Template de perfil** completo com informações de sessão
- ✅ **Middleware personalizado** para gestão de papéis de utilizador
- ✅ **Gestão de sessões** com opção "manter sessão iniciada"
- ✅ **Sistema de mensagens** de feedback para login/logout
- ✅ **Perfis de acesso** preparados: admin, staff, instrutor, cliente

**🎉 STATUS: FASE 1 100% CONCLUÍDA - SISTEMA WEB COMPLETO E FUNCIONAL**

---

### **📊 RESUMO GERAL DO PROGRESSO**

#### **✅ FASES CONCLUÍDAS**
- **✅ PASSO 1** - Problema "Empty Compose File" (100% resolvido)
- **✅ PASSO 2** - Django Admin Unificado (100% implementado)
- **✅ FASE 1** - Interface Web + GANTT (100% concluída)

#### **🎯 PRÓXIMA PRIORIDADE**
Nenhuma, todas as fases concluídas.

#### **🏆 PRINCIPAIS CONQUISTAS**
1. **Sistema CRUD Completo** implementado para todas as entidades principais
2. **Interface Web Moderna** com Bootstrap 5 e componentes responsivos
3. **Templates Avançados** com filtros, paginação e validações
4. **Dashboard Interativo** com KPIs e estatísticas em tempo real
5. **Sistema Gantt** funcional para gestão de espaços
6. **Arquitetura Multi-Entidade** (ACR + Proform) totalmente funcional

#### **🚀 ESTADO ATUAL DO PROJETO**
- **Interface Admin**: ✅ Funcional e moderna
- **API REST**: ✅ Completa e documentada  
- **Templates Web**: ✅ Sistema CRUD completo
- **Dashboard**: ✅ Interativo com estatísticas
- **Sistema Gantt**: ✅ Implementado e funcional
- **Autenticação Web**: ✅ Completa e funcional

**PROGRESSO TOTAL FASE 1: 100% CONCLUÍDA**

---

### **🔧 INFORMAÇÕES TÉCNICAS**

#### **Templates CRUD Implementados**
- ✅ `client_list.html` - Listagem de clientes com filtros
- ✅ `client_form.html` - Formulário moderno de clientes
- ✅ `client_detail.html` - Página de detalhes completa
- ✅ `instructor_list.html` - Listagem grid/tabela de instrutores
- ✅ `instructor_form.html` - Formulário avançado de instrutores
- ✅ `instructor_detail.html` - Detalhes com próximas aulas e comissões
- ✅ `event_list.html` - Listagem avançada de aulas/eventos
- ✅ `base.html` - Template base moderno e responsivo

#### **URLs Configuradas**
- ✅ Sistema completo de rotas para todos os CRUDs
- ✅ Views otimizadas com filtros e paginação
- ✅ API JSON para integração com Sistema Gantt
- ✅ Breadcrumbs e navegação intuitiva

#### **Funcionalidades Avançadas**
- ✅ Upload de fotos para clientes e instrutores
- ✅ Filtros avançados por período, modalidade, instrutor
- ✅ Paginação automática em todas as listagens
- ✅ Validação de formulários com JavaScript
- ✅ Sistema de mensagens de feedback
- ✅ Responsive design para mobile/tablet

**STATUS: 🎉 TEMPLATES CRUD 100% IMPLEMENTADOS E FUNCIONAIS**

---

## 🎯 PRÓXIMAS PRIORIDADES - FASE 2
Com a FASE 1 100% concluída, as próximas prioridades são:

### **🚀 FASE 2 - INTEGRAÇÕES EXTERNAS (PRÓXIMA)** 
**Estado: 0% - A INICIAR**

#### **📱 Integração Google Calendar (PRIORITÁRIO)**
- [ ] **Configuração OAuth2** para Google Calendar API
- [ ] **Exportação individual** das marcações de cada instrutor
- [ ] **Sincronização bidirecional** (ACR → Google Calendar)
- [ ] **Calendários separados** por instrutor e entidade
- [ ] **Notificações automáticas** de mudanças e atualizações
- [ ] **Partilha de calendários** entre equipa e gestão
- [ ] **Interface de configuração** no admin para tokens

#### **☁️ Sistema de Backups Google Drive (IMPORTANTE)**
- [ ] **Configuração OAuth2** para Google Drive API
- [ ] **Backup automático** da base de dados (diário/semanal)
- [ ] **Exportação Excel** completa de clientes por entidade
- [ ] **Relatórios automáticos** em Excel/PDF mensais
- [ ] **Versionamento de backups** com rotação automática
- [ ] **Sistema de restore** automático a partir de backups
- [ ] **Notificações email** de backup (sucesso/erro)
- [ ] **Dashboard de monitorização** de backups

#### **📊 Relatórios e Analytics Avançados**
- [ ] **Relatórios de ocupação** por espaço e modalidade
- [ ] **Analytics de clientes** (frequência, preferências)
- [ ] **Relatórios financeiros** por entidade (ACR/Proform)
- [ ] **Dashboard de comissões** para instrutores
- [ ] **Exportação de dados** em múltiplos formatos
- [ ] **Gráficos interativos** com Chart.js

### **🚀 FASE 3 - FUNCIONALIDADES AVANÇADAS (FUTURO)**
**Estado: 0% - PLANEAMENTO**

#### **💳 Sistema de Pagamentos Online**
- [ ] **Integração Stripe/PayPal** para pagamentos online
- [ ] **Portal do cliente** para pagamentos automáticos
- [ ] **Gestão de mensalidades** automática
- [ ] **Faturas digitais** com geração automática
- [ ] **Lembretes de pagamento** por email/SMS

#### **📱 Aplicação Mobile (React Native)**
- [ ] **App móvel** para clientes (reservas, horários)
- [ ] **App para instrutores** (agenda, comissões)
- [ ] **Notificações push** para aulas e alterações
- [ ] **Check-in QR Code** para aulas
- [ ] **Sincronização offline** básica

#### **🤖 Automações e IA**
- [ ] **Sugestões de horários** baseadas em ocupação
- [ ] **Previsão de cancelamentos** com machine learning
- [ ] **Chatbot** para atendimento básico
- [ ] **Análise de sentimentos** em feedback de clientes

### **🚀 FASE 4 - EXPANSÃO E OTIMIZAÇÃO (LONGO PRAZO)**
**Estado: 0% - CONCEITO**

#### **🌐 Multi-Tenant Completo**
- [ ] **Sistema SaaS** para múltiplos ginásios
- [ ] **Planos de subscrição** diferenciados
- [ ] **Domínios personalizados** por cliente
- [ ] **Branding personalizado** por organização

#### **⚡ Performance e Escalabilidade**
- [ ] **Otimização de queries** e caching avançado
- [ ] **CDN** para assets estáticos
- [ ] **Load balancing** para alta disponibilidade
- [ ] **Monitoring** avançado com métricas detalhadas

#### **🔐 Segurança Avançada**
- [ ] **Autenticação 2FA** obrigatória
- [ ] **Auditoria completa** de ações de utilizadores
- [ ] **Compliance RGPD** total
- [ ] **Penetration testing** regular
