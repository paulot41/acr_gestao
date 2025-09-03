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

### **Modelos Existentes**
- `Organization` - Entidade tenant (multi-tenant)
- `Person` - Clientes/atletas
- `Membership` - Subscrições/memberships
- `Product` - Produtos/serviços faturáveis
- `Price` - Preços com validade temporal
- `Resource` - Recursos bookáveis (salas/espaços)
- `ClassTemplate` - Templates para aulas recorrentes
- `Event` - Eventos/aulas agendadas
- `Booking` - Reservas de clientes para eventos

### **APIs Existentes**
- PersonViewSet - CRUD de clientes
- MembershipViewSet - CRUD de memberships
- ProductViewSet - CRUD de produtos
- EventViewSet - CRUD de eventos com booking
- BookingViewSet - CRUD de reservas

---

## 🎯 FUNCIONALIDADES ESPECÍFICAS SOLICITADAS

### 📅 **SISTEMA GANTT PARA ESPAÇOS**
**Espaços disponíveis:**
- Ginásio
- Sala de Pilates
- Pavilhão

**Funcionalidades:**
- Interface Gantt interativa para marcação
- Visualização de ocupação por espaço/instrutor
- Drag & drop para marcações rápidas
- Cores diferentes por modalidade/instrutor
- Detecção visual de conflitos
- Marcações recorrentes (semanais/mensais)

### 🏋️ **GESTÃO DE MODALIDADES**
- Adição manual de modalidades
- Associação modalidade-instrutor-espaço
- Definição de capacidade máxima
- Duração típica por modalidade

### 📱 **INTEGRAÇÃO GOOGLE CALENDAR**
- Exportação individual das marcações de cada instrutor
- Sincronização bidirecional
- Notificações automáticas de mudanças
- Partilha de calendários entre equipa

### ☁️ **SISTEMA DE BACKUPS GOOGLE DRIVE**
- Backup automático da base de dados (diário/semanal)
- Exportação Excel completa de clientes
- Relatórios automáticos em Excel/PDF
- Versionamento de backups
- Restore automático
- Notificações de backup (sucesso/erro)

---

## 📋 ROADMAP DE DESENVOLVIMENTO

### **FASE 1 - INTERFACE WEB + GANTT (6-8 semanas)**
**Prioridade: ALTA**

#### Templates e Interface Base
- [ ] Criar sistema de templates Django
- [ ] Template base (base.html) com Bootstrap 5
- [ ] Navbar com navegação principal
- [ ] Footer e estrutura responsiva
- [ ] Sistema de mensagens/alerts

#### Sistema de Autenticação Web
- [ ] Páginas de login/logout
- [ ] Gestão de utilizadores
- [ ] Middleware de autenticação web
- [ ] Perfis diferentes (admin, rececionista, instrutor)

#### CRUD Web Completo
- [ ] Listagem de clientes com filtros e paginação
- [ ] Formulários para criar/editar clientes
- [ ] Páginas de detalhes
- [ ] Confirmações de eliminação
- [ ] CRUD de modalidades
- [ ] CRUD de instrutores

#### Interface Gantt
- [ ] Implementar FullCalendar.js ou DHTMLX Gantt
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

---

### **FASE 2 - INTEGRAÇÕES E BACKUPS (4-6 semanas)**
**Prioridade: ALTA**

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
- [ ] Modelo Payment/Pagamento
- [ ] Registo de pagamentos por cliente
- [ ] Métodos de pagamento (dinheiro, cartão, transferência)
- [ ] Relatórios financeiros básicos
- [ ] Alertas de pagamentos em atraso

---

### **FASE 3 - FUNCIONALIDADES AVANÇADAS (8-10 semanas)**
**Prioridade: MÉDIA**

#### Portal do Cliente
- [ ] Área restrita para clientes
- [ ] Visualização de horários e reservas
- [ ] Histórico de pagamentos
- [ ] Alteração de dados pessoais

#### Sistema de Notificações
- [ ] SMS automáticos (Twilio)
- [ ] Lembretes de pagamento por email
- [ ] Notificações de cancelamentos
- [ ] Alertas de aniversário

#### Relatórios Avançados
- [ ] Ocupação média por espaço/horário
- [ ] Análise de rentabilidade por modalidade
- [ ] Frequência de clientes
- [ ] Performance de instrutores
- [ ] Exportação PDF/Excel

#### Pagamentos Online
- [ ] Integração Stripe/PayPal
- [ ] Faturação automática
- [ ] Débitos diretos
- [ ] Gestão de reembolsos

---

### **FASE 4 - OTIMIZAÇÕES (4-6 semanas)**
**Prioridade: BAIXA**

#### App Móvel Básica
- [ ] React Native ou Flutter
- [ ] Check-in por QR Code
- [ ] Reservas móveis

#### Analytics Avançados
- [ ] Previsão de receitas
- [ ] Análise de retenção
- [ ] Campanhas de marketing

#### Funcionalidades Extras
- [ ] Sistema de pontos/fidelização
- [ ] Avaliações físicas
- [ ] Planos nutricionais básicos

---

## 🔧 TECNOLOGIAS E BIBLIOTECAS SUGERIDAS

### Frontend
- **Bootstrap 5** - Framework CSS responsivo
- **FullCalendar.js** - Interface Gantt/Calendar
- **Chart.js** - Gráficos e dashboards
- **jQuery** - Manipulação DOM
- **SweetAlert2** - Modals e confirmações

### Backend & APIs
- **Google Calendar API** - Sincronização calendários
- **Google Drive API** - Backups automáticos
- **openpyxl** - Geração de ficheiros Excel
- **Celery + Redis** - Tarefas assíncronas
- **Twilio** - Envio de SMS
- **Stripe/PayPal** - Pagamentos online

### Deploy & Infraestrutura
- **Docker** - Containerização
- **Nginx** - Reverse proxy
- **PostgreSQL** - Base de dados produção
- **Redis** - Cache e message broker

---

## 📁 ESTRUTURA DE FICHEIROS PLANEADA

```
acr_gestao/
├── core/
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── clients/
│   │   ├── instructors/
│   │   ├── bookings/
│   │   └── gantt/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   ├── management/
│   │   └── commands/
│   ├── services/
│   │   ├── google_calendar.py
│   │   ├── google_drive.py
│   │   ├── backup.py
│   │   └── notifications.py
│   └── models/ (expandir existentes)
├── requirements.txt (atualizar)
└── PROJECT_GUIDE.md (este ficheiro)
```

---

## 💾 MELHORIAS NOS MODELOS EXISTENTES

### Modelo Person (Cliente)
```python
# Campos a adicionar:
date_of_birth = models.DateField(null=True, blank=True)
address = models.TextField(blank=True)
emergency_contact = models.CharField(max_length=100, blank=True)
photo = models.ImageField(upload_to='clients/', null=True, blank=True)
status = models.CharField(max_length=20, choices=Status.choices, default='active')
created_at = models.DateTimeField(auto_now_add=True)
last_activity = models.DateTimeField(null=True, blank=True)
```

### Novos Modelos Necessários
- **Instructor** - Instrutores/Personal Trainers
- **Modality** - Modalidades (pilates, musculação, etc.)
- **Payment** - Pagamentos dos clientes
- **Notification** - Sistema de notificações
- **BackupLog** - Logs de backups

---

## 🚀 COMO USAR ESTE GUIA

1. **Para novas conversações**: Referencia este ficheiro para contexto completo
2. **Para desenvolvimento**: Seguir as fases do roadmap por ordem
3. **Para atualizações**: Manter este ficheiro sempre atualizado
4. **Para deploy**: Usar os scripts existentes na raiz do projeto

---

## 📞 REFERÊNCIA RÁPIDA

### Comandos úteis
```bash
# Desenvolvimento
python manage.py runserver
python manage.py makemigrations
python manage.py migrate

# Deploy
./deploy.sh
docker-compose -f docker-compose.base-nginx.yml up -d

# Backup manual
python manage.py backup_to_drive
```

### URLs importantes
- API Root: `/api/`
- Admin: `/admin/`
- Documentação API: `/api/docs/`

---

**Última atualização:** 3 de setembro de 2025
**Versão:** 1.0
**Estado:** API REST funcional, interface web em desenvolvimento
