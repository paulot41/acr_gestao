# 🏋️‍♂️ ACR Gestão - Sistema de Gestão para Ginásios e Wellness

## ✨ **VERSÃO ATUAL - Dashboard Personalizado & Admin Completo**

Sistema completo de gestão multi-entidade para ginásios (ACR) e centros de wellness (Proform) com **Dashboard personalizado como página inicial** e **Django Admin totalmente funcional**.

## Atualizações recentes

- Substituição de `except Exception` por exceções específicas com registo adequado.
- Remoção da criação automática de organização em `get_current_organization`.
- Consolidação do middleware de multi-tenancy.
- Cálculos financeiros agora utilizam `Decimal` para maior precisão.
- Migração de `unique_together` para `UniqueConstraint` nos modelos.
- Limpeza de imports não utilizados no middleware core.
- Adição de testes automatizados para modelos e middleware.

### 🚀 **Funcionalidades Principais**

#### 📊 **Dashboard Personalizado (NOVIDADE!)**
- **Página inicial intuitiva** com estatísticas em tempo real
- **Navegação superior completa** com menus dropdown organizados
- **Ações rápidas** para funcionalidades mais usadas
- **Interface responsiva** com Bootstrap 5
- **Alertas visuais** para créditos baixos e eventos importantes
- **Design moderno** com cards e gradientes

#### ⚙️ **Django Admin Completo**
- **Todos os modelos registados** com interfaces personalizadas
- **Multi-tenancy** - cada organização vê apenas os seus dados
- **CRUD completo** para gestão avançada
- **Filtros e pesquisas** otimizadas
- **Fieldsets organizados** para melhor UX

#### 🎯 **Gantt Dinâmico**
- **Drag & Drop** para criação instantânea de aulas
- **Interface moderna** com espaços à esquerda e horas no topo
- **Linha de tempo atual** em tempo real
- **Vista 6h-22h ou 24h** configurável
- **Três tipos de aulas**: Abertas, Turmas e Individuais
- **Validação automática** de conflitos de horário

#### 👥 **Sistema de Turmas Completo**
- **Gestão de turmas** com modalidades específicas
- **Membros por turma** com controlo de capacidade
- **Níveis configuráveis** (Iniciante, Intermédio, Avançado)
- **Integração perfeita** com o Gantt dinâmico
- **Admin interface** dedicada

#### 🏢 **Multi-Tenancy Robusto**
- **Isolamento completo** de dados por organização
- **Domínios personalizados** (acr.local, proform.local)
- **Configurações independentes** por entidade
- **Tipos**: Ginásio, Wellness ou Ambos

#### 💰 **Gestão Financeira**
- **Planos flexíveis**: Mensalidades, Créditos, Ilimitados
- **Sistema de créditos** automático
- **Comissões por instrutor** configuráveis
- **Relatórios financeiros** detalhados

#### 📱 **Interface Moderna**
- **Design responsivo** com Bootstrap 5
- **Dashboard personalizado** por tipo de utilizador
- **Navegação intuitiva** com menus dropdown
- **Cores personalizadas** por modalidade
- **Animações suaves** e feedback visual

---

## 📋 **Tecnologias Utilizadas**

### Backend:
- **Django 5.1.1** - Framework principal
- **PostgreSQL** - Base de dados principal
- **Redis** - Cache e sessões
- **Django REST Framework** - APIs otimizadas

### Frontend:
- **HTML5/CSS3** moderno
- **JavaScript ES6+** para interatividade
- **Bootstrap 5.3.0** - Framework CSS responsivo via CDN
- **Font Awesome 6.0** - Iconografia moderna
- **FullCalendar 6.1.8** - Calendário Gantt interativo

### DevOps:
- **Docker & Docker Compose** - Containerização
- **Nginx** - Proxy reverso com SSL automático
- **GitHub Actions** - CI/CD (preparado)

---

## 🎨 **Bootstrap 5 - Interface Moderna**

O projeto utiliza **Bootstrap 5.3.0** para uma interface moderna e responsiva:

### Componentes Principais:
- **Navbar responsiva** com dropdown menus
- **Grid system flexível** para layout adaptativo
- **Cards e shadows** para organização visual
- **Badges e buttons** com cores personalizadas
- **Tables responsivas** para dados

### Integração Django + Bootstrap:
```html
<!-- Template base com Bootstrap 5 -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<!-- Classes Bootstrap utilizadas -->
<div class="container-fluid">
    <div class="row">
        <div class="col-lg-6">
            <div class="card shadow-sm">
                <div class="card-body">
                    <!-- Conteúdo -->
                </div>
            </div>
        </div>
    </div>
</div>
```

### Vantagens do Bootstrap 5:
- ✅ **Design responsivo automático**
- ✅ **Componentes prontos a usar**
- ✅ **Compatibilidade cross-browser**
- ✅ **Customização via CSS variáveis**
- ✅ **Performance otimizada**

---

## 🚀 **Instalação Rápida**

### Acesso ao Sistema:
- **Dashboard**: `http://localhost:8000/` (página inicial)
- **Admin Django**: `http://localhost:8000/admin/`
- **Vista Gantt**: `http://localhost:8000/gantt/`

### Desenvolvimento Local (Docker):
```bash
# Clonar repositório
git clone https://github.com/paulot41/acr_gestao.git
cd acr_gestao

# Iniciar com Docker
docker-compose up -d

# Criar dados básicos
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### Desenvolvimento Manual:
```bash
# Configurar ambiente Python
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Base de dados
python manage.py migrate
python manage.py createsuperuser

# Executar
python manage.py runserver
```

---

## 🏗️ **Estrutura do Projeto**

### URLs Principais:
```
/                    → Dashboard personalizado (página inicial)
/admin/             → Django Admin completo
/gantt/             → Vista Gantt interativa
/api/               → APIs REST
```

### Navegação Superior:
- **Dashboard** - Visão geral com estatísticas
- **Calendário** - Vista Gantt para agendamento
- **Clientes** - Gestão completa de clientes
- **Instrutores** - Gestão de instrutores
- **Eventos** - Criação e gestão de eventos
- **Google Calendar** - Sincronização automática

...existing code...
