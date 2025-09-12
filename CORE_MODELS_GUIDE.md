# 📚 Documentação Completa - Core Models

## 🏢 **Organization** - Entidade Multi-tenant
Representa cada organização/cliente do sistema (ACR, Proform, etc.)

### Atualizações recentes

- Substituição de `except Exception` por exceções específicas com registo.
- Remoção da criação automática de organização em `get_current_organization`.
- Middleware de multi-tenancy consolidado.
- Cálculos financeiros baseados em `Decimal`.
- Migração para `UniqueConstraint` no modelo `Person`.
- Limpeza de imports não utilizados.
- Novos testes automatizados para `Person` e `OrganizationMiddleware`.

### Atributos:
- **name**: Nome da organização
- **domain**: Domínio único (ex: acr.local, proform.local)
- **org_type**: Tipo de organização
  - `gym`: Ginásio (ACR)
  - `wellness`: Pilates/Wellness (Proform) 
  - `both`: Ambos (ACR + Proform)
- **settings_json**: Configurações personalizadas (JSON)
- **gym_monthly_fee**: Mensalidade do ginásio (€30.00 padrão)
- **wellness_monthly_fee**: Mensalidade wellness (€45.00 padrão)

### Métodos:
- **__str__()**: Retorna nome + tipo de organização

---

## 👤 **Person** - Clientes/Atletas
Representa os clientes da organização

### Atributos Básicos:
- **organization**: Organização a que pertence (FK)
- **first_name**: Nome próprio (obrigatório)
- **last_name**: Apelido
- **email**: Email (único por organização)
- **nif**: Número de contribuinte (único por organização)
- **phone**: Telefone

### Dados Pessoais:
- **date_of_birth**: Data de nascimento
- **address**: Morada completa
- **emergency_contact**: Contacto de emergência
- **photo**: Foto do cliente

### Status e Afiliação:
- **status**: Estado do cliente
  - `active`: Ativo
  - `inactive`: Inativo
  - `suspended`: Suspenso
- **entity_affiliation**: Afiliação à entidade
  - `acr_only`: Apenas ACR (Ginásio)
  - `proform_only`: Apenas Proform (Pilates)
  - `both`: ACR + Proform

### Metadados:
- **notes**: Notas adicionais
- **created_at**: Data de criação
- **last_activity**: Última atividade

### Métodos:
- **full_name**: Propriedade que retorna nome completo
- **get_monthly_fee()**: Calcula mensalidade baseada na afiliação
- **__str__()**: Retorna nome + afiliação

---

## 🏃‍♂️ **Instructor** - Instrutores/Personal Trainers
Representa os instrutores da organização

### Atributos Básicos:
- **organization**: Organização a que pertence (FK)
- **first_name**: Nome próprio
- **last_name**: Apelido
- **email**: Email (único por organização)
- **phone**: Telefone
- **photo**: Foto do instrutor

### Qualificações:
- **specialties**: Especialidades e certificações
- **entity_affiliation**: Para que entidade trabalha
  - `acr_only`: Apenas ACR
  - `proform_only`: Apenas Proform
  - `both`: ACR + Proform

### Configurações Financeiras:
- **acr_commission_rate**: Taxa de comissão ACR (% - padrão 60%)
- **proform_commission_rate**: Taxa de comissão Proform (% - padrão 70%)

### Status:
- **is_active**: Se está ativo
- **created_at**: Data de criação

### Métodos:
- **full_name**: Propriedade que retorna nome completo
- **__str__()**: Retorna nome + afiliação

---

## 🏃‍♀️ **Modality** - Modalidades de Exercício
Representa as modalidades disponíveis (Pilates, Musculação, etc.)

### Atributos Básicos:
- **organization**: Organização (FK)
- **name**: Nome da modalidade
- **description**: Descrição detalhada

### Configurações:
- **default_duration_minutes**: Duração padrão em minutos (60 min padrão)
- **max_capacity**: Capacidade máxima de participantes (10 padrão)
- **color**: Cor hexadecimal para o Gantt (#0d6efd padrão)

### Entidade:
- **entity_type**: A que entidade pertence
  - `acr`: ACR (Ginásio)
  - `proform`: Proform (Pilates/Wellness)
  - `both`: Ambas

### Status:
- **is_active**: Se está ativa
- **created_at**: Data de criação

### Métodos:
- **__str__()**: Retorna nome + entidade

---

## 🏢 **Resource** - Espaços/Recursos
Representa os espaços físicos reserváveis

### Atributos Básicos:
- **organization**: Organização (FK)
- **name**: Nome do espaço
- **description**: Descrição detalhada
- **capacity**: Capacidade máxima

### Entidade:
- **entity_type**: A que entidade pertence
  - `acr`: ACR (Ginásio)
  - `proform`: Proform (Pilates/Wellness)
  - `both`: Ambas

### Equipamentos:
- **equipment_list**: Lista de equipamentos disponíveis
- **special_features**: Características especiais

### Disponibilidade:
- **is_available**: Se está disponível para uso
- **created_at**: Data de criação
- **updated_at**: Última atualização

### Métodos:
- **__str__()**: Retorna nome + entidade + capacidade

---

## 👥 **ClassGroup** - Turmas/Grupos
Representa turmas de clientes para aulas em grupo

### Atributos Básicos:
- **organization**: Organização (FK)
- **name**: Nome da turma
- **description**: Descrição
- **modality**: Modalidade associada (FK)
- **instructor**: Instrutor responsável (FK - opcional)

### Configurações:
- **max_students**: Máximo de alunos
- **level**: Nível da turma (Iniciante, Intermédio, Avançado)

### Membros:
- **members**: Clientes inscritos (ManyToMany com Person)

### Datas:
- **start_date**: Data de início
- **end_date**: Data de fim
- **is_active**: Se está ativa

### Metadados:
- **created_at**: Data de criação
- **updated_at**: Última atualização

### Propriedades:
- **current_members_count**: Número atual de membros ativos
- **has_availability**: Se tem vagas disponíveis

### Métodos:
- **__str__()**: Retorna nome + modalidade

---

## 📅 **Event** - Eventos/Aulas
Representa aulas agendadas no sistema

### Atributos Básicos:
- **organization**: Organização (FK)
- **resource**: Espaço onde ocorre (FK)
- **modality**: Modalidade (FK - opcional)
- **instructor**: Instrutor (FK - opcional)

### Tipo de Evento:
- **event_type**: Tipo de aula
  - `group_class`: Aula de Turma
  - `individual`: Aula Individual
  - `open_class`: Aula Aberta

### Participantes (baseado no tipo):
- **class_group**: Turma associada (para aulas de turma)
- **individual_client**: Cliente individual (para aulas 1-1)

### Detalhes:
- **title**: Título do evento
- **description**: Descrição
- **capacity**: Capacidade máxima

### Horários:
- **starts_at**: Data/hora de início
- **ends_at**: Data/hora de fim

### Google Calendar:
- **google_calendar_id**: ID no Google Calendar
- **google_calendar_sync_enabled**: Se sincroniza com Google
- **last_google_sync**: Última sincronização

### Propriedades:
- **bookings_count**: Número de reservas confirmadas
- **is_full**: Se está lotado
- **display_title**: Título personalizado baseado no tipo

### Métodos:
- **clean()**: Validações personalizadas
- **__str__()**: Retorna título + data/hora

---

## 🎫 **Booking** - Reservas
Representa reservas de clientes para eventos

### Atributos Básicos:
- **organization**: Organização (FK)
- **event**: Evento reservado (FK)
- **person**: Cliente que reservou (FK)

### Status:
- **status**: Estado da reserva
  - `confirmed`: Confirmada
  - `cancelled`: Cancelada

### Sistema de Créditos:
- **subscription_used**: Subscrição utilizada (FK - opcional)
- **credits_used**: Número de créditos utilizados (1 padrão)
- **is_paid**: Se foi pago fora do sistema de créditos
- **payment_amount**: Valor pago diretamente

### Datas:
- **created_at**: Data de criação
- **cancelled_at**: Data de cancelamento

### Métodos:
- **clean()**: Validações de capacidade e créditos
- **can_be_cancelled()**: Se pode ser cancelada (até 2h antes)
- **save()**: Auto-consumo de créditos

### Regras:
- Única reserva por pessoa/evento
- Auto-consumo de créditos na confirmação
- Devolução de créditos no cancelamento

---

## 💳 **PaymentPlan** - Planos de Pagamento
Representa planos flexíveis de mensalidades e créditos

### Atributos Básicos:
- **organization**: Organização (FK)
- **name**: Nome do plano
- **description**: Descrição

### Tipo:
- **plan_type**: Tipo de plano
  - `monthly`: Mensalidade
  - `credits`: Créditos para Aulas
  - `unlimited`: Ilimitado

### Entidade:
- **entity_type**: Entidade aplicável
  - `acr`: ACR (Ginásio)
  - `proform`: Proform (Pilates/Wellness)
  - `both`: Ambas

### Preço e Duração:
- **price**: Preço do plano
- **duration_months**: Duração em meses (1 padrão)

### Créditos (para planos de crédito):
- **credits_included**: Número de aulas incluídas
- **credits_validity_days**: Validade dos créditos (30 dias padrão)

### Modalidades:
- **modalities**: Modalidades incluídas (ManyToMany - opcional)

### Status:
- **is_active**: Se está ativo
- **created_at**: Data de criação
- **updated_at**: Última atualização

---

## 📊 **ClientSubscription** - Subscrições de Clientes
Representa subscrições ativas dos clientes aos planos

### Atributos Básicos:
- **organization**: Organização (FK)
- **person**: Cliente (FK)
- **payment_plan**: Plano associado (FK)

### Status:
- **status**: Estado da subscrição
  - `active`: Ativo
  - `expired`: Expirado
  - `suspended`: Suspenso
  - `cancelled`: Cancelado

### Datas:
- **start_date**: Data de início
- **end_date**: Data de fim

### Créditos:
- **remaining_credits**: Créditos restantes
- **credits_expire_date**: Data de expiração dos créditos

### Pagamento:
- **is_paid**: Se foi pago
- **payment_date**: Data de pagamento

### Metadados:
- **notes**: Notas
- **created_at**: Data de criação
- **updated_at**: Última atualização

### Métodos:
- **has_credits()**: Se tem créditos disponíveis
- **use_credit()**: Consome um crédito

---

## 💰 **Payment** - Pagamentos
Regista pagamentos dos clientes

### Atributos Básicos:
- **organization**: Organização (FK)
- **person**: Cliente (FK)
- **amount**: Valor

### Método:
- **method**: Método de pagamento
  - `cash`: Dinheiro
  - `card`: Cartão
  - `transfer`: Transferência
  - `mbway`: MB WAY
  - `other`: Outro

### Status:
- **status**: Estado do pagamento
  - `pending`: Pendente
  - `completed`: Pago
  - `cancelled`: Cancelado
  - `refunded`: Reembolsado

### Detalhes:
- **description**: Descrição
- **notes**: Notas

### Datas:
- **due_date**: Data de vencimento
- **paid_date**: Data de pagamento
- **created_at**: Data de criação
- **updated_at**: Última atualização

### Métodos:
- **is_overdue()**: Se está em atraso

---

## 🤝 **InstructorCommission** - Comissões de Instrutores
Calcula e regista comissões por aula

### Atributos Básicos:
- **instructor**: Instrutor (FK)
- **event**: Evento/aula (FK)
- **organization**: Organização (FK)

### Valores Financeiros:
- **total_revenue**: Receita total da aula
- **instructor_amount**: Valor para o instrutor
- **entity_amount**: Valor para a entidade
- **commission_rate**: Taxa de comissão aplicada

### Controlo:
- **is_paid**: Se foi pago ao instrutor
- **payment_date**: Data de pagamento
- **notes**: Notas
- **created_at**: Data de criação

### Métodos:
- **save()**: Auto-calcula valores baseados na comissão

---

## 🔔 **Google Calendar Integration**
Sistema de integração com Google Calendar

### GoogleCalendarConfig:
- Configuração OAuth2 por organização
- Tokens de acesso e refresh
- Configurações de sincronização

### InstructorGoogleCalendar:
- Calendário individual por instrutor
- Configurações de privacidade
- Filtros de sincronização

### GoogleCalendarSyncLog:
- Log de todas as sincronizações
- Rastreamento de erros
- Metadados de sincronização

---

## 🔗 **Relacionamentos Principais**

### Hierarquia Organizacional:
```
Organization
├── Person (Clientes)
├── Instructor (Instrutores)
├── Modality (Modalidades)
├── Resource (Espaços)
├── ClassGroup (Turmas)
├── PaymentPlan (Planos)
└── Event (Aulas)
```

### Fluxo de Reservas:
```
Person → ClientSubscription → PaymentPlan
Person → Booking → Event → Resource
ClassGroup → Event → Resource
```

### Sistema de Créditos:
```
PaymentPlan → ClientSubscription → Booking
Credits: Consumed on booking, returned on cancellation
```

---

## 📈 **Índices de Performance**

### Event:
- organization + starts_at
- organization + resource + starts_at

### Person:
- organization + email (único)
- organization + nif (único)

### Unique Together:
- Person: (organization, email), (organization, nif)
- Instructor: (organization, email)
- Modality: (organization, name)
- Resource: (organization, name)
- ClassGroup: (organization, name)
- Booking: (event, person)

---

## 🎯 **Validações Automáticas**

### Event.clean():
- Validar horários (fim > início)
- Configurar capacidade por tipo
- Verificar conflitos de espaço

### Booking.clean():
- Validar capacidade do evento
- Verificar créditos disponíveis

### Form Validations:
- Email único por organização
- NIF português válido
- Conflitos de horário em tempo real

Este modelo é otimizado para **multi-tenancy**, **performance** e **escalabilidade**, suportando múltiplas organizações com isolamento completo de dados.
