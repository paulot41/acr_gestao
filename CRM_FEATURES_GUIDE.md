# 📊 GUIA DE FUNCIONALIDADES CRM E AVANÇADAS - ACR GESTÃO
# ================================================================

## 🎯 **VISÃO GERAL**

Este documento detalha as funcionalidades avançadas planejadas para transformar o ACR Gestão num sistema CRM completo para ginásios, com automação de marketing, análises avançadas e conformidade RGPD.

### Atualizações recentes

- Substituição de `except Exception` por exceções específicas com logging.
- Remoção da criação automática de organização em `get_current_organization`.
- Consolidação do middleware de multi-tenancy.
- Cálculos monetários com `Decimal`.
- Migração de `unique_together` para `UniqueConstraint`.
- Limpeza de imports redundantes.
- Adição de testes automatizados para modelos e middleware.

### 🏆 **OBJETIVOS PRINCIPAIS**
- **🔄 Automação completa** do ciclo de vida do cliente
- **📊 Inteligência de negócio** com previsões ML
- **📱 Experiência móvel nativa** para todos os utilizadores
- **🔒 Conformidade legal** 100% com RGPD
- **💰 Otimização de receitas** através de dados

---

## 📊 **1. SISTEMA CRM INTEGRADO**

### **Gestão Avançada de Sócios**

#### **Perfil 360º do Cliente:**
```python
class EnhancedPersonProfile(models.Model):
    person = models.OneToOneField(Person, related_name='enhanced_profile')
    
    # Dados comportamentais
    attendance_pattern = models.JSONField(default=dict)  # Padrões de frequência
    preferred_times = models.JSONField(default=list)     # Horários preferenciais
    favorite_modalities = models.ManyToManyField(Modality)
    
    # Scoring e segmentação
    loyalty_score = models.IntegerField(default=0)       # 0-100
    churn_risk = models.FloatField(default=0.0)         # 0.0-1.0
    lifetime_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Preferências de comunicação
    communication_preferences = models.JSONField(default=dict)
    
    # Dados calculados automaticamente
    last_activity = models.DateTimeField(null=True)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    months_active = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Perfil Avançado"
        verbose_name_plural = "Perfis Avançados"
    
    def calculate_loyalty_score(self):
        """Calcula score de fidelização baseado em múltiplos fatores"""
        score = 0
        
        # Frequência (40% do score)
        monthly_visits = self.get_monthly_visits()
        if monthly_visits >= 12: score += 40
        elif monthly_visits >= 8: score += 30
        elif monthly_visits >= 4: score += 20
        
        # Pontualidade (20% do score)
        punctuality_rate = self.get_punctuality_rate()
        score += int(punctuality_rate * 20)
        
        # Tempo como cliente (20% do score)
        if self.months_active >= 12: score += 20
        elif self.months_active >= 6: score += 15
        elif self.months_active >= 3: score += 10
        
        # Engagement (20% do score)
        engagement_rate = self.get_engagement_rate()
        score += int(engagement_rate * 20)
        
        return min(score, 100)
    
    def predict_churn_risk(self):
        """Usa ML para prever risco de abandono"""
        from core.ml_models import ChurnPredictor
        
        features = {
            'days_since_last_visit': self.get_days_since_last_visit(),
            'avg_monthly_visits': self.get_avg_monthly_visits(),
            'total_spent': float(self.total_revenue),
            'loyalty_score': self.loyalty_score,
            'months_active': self.months_active
        }
        
        return ChurnPredictor.predict_churn_probability(features)
```

#### **Histórico Completo de Interações:**
```python
class CustomerInteraction(models.Model):
    INTERACTION_TYPES = [
        ('visit', 'Visita ao Ginásio'),
        ('class_booking', 'Reserva de Aula'),
        ('payment', 'Pagamento'),
        ('email_open', 'Email Aberto'),
        ('email_click', 'Click em Email'),
        ('sms_received', 'SMS Recebido'),
        ('app_login', 'Login na App'),
        ('support_contact', 'Contacto Suporte'),
        ('complaint', 'Reclamação'),
        ('compliment', 'Elogio'),
    ]
    
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)
    source = models.CharField(max_length=50)  # web, mobile, email, etc.
    
    # Contextualização
    session_id = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['person', '-timestamp']),
            models.Index(fields=['interaction_type', '-timestamp']),
        ]
```

---

## 📧 **2. MARKETING AUTOMATION**

### **Sistema de Campanhas Inteligentes**

#### **Automação Baseada em Triggers:**
```python
class MarketingAutomation(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Configuração do trigger
    trigger_event = models.CharField(max_length=50, choices=[
        ('new_member', 'Novo Sócio'),
        ('birthday', 'Aniversário'),
        ('membership_expiring', 'Mensalidade a Expirar'),
        ('no_activity_7days', 'Sem Atividade 7 Dias'),
        ('no_activity_30days', 'Sem Atividade 30 Dias'),
        ('high_loyalty_score', 'Score Alto de Fidelização'),
        ('low_loyalty_score', 'Score Baixo de Fidelização'),
        ('first_class_completed', 'Primeira Aula Completa'),
        ('10_classes_completed', '10 Aulas Completadas'),
    ])
    
    # Condições adicionais
    target_segment = models.JSONField(default=dict)  # Critérios de segmentação
    
    # Ações a executar
    email_template = models.ForeignKey('EmailTemplate', null=True, blank=True)
    sms_template = models.ForeignKey('SMSTemplate', null=True, blank=True)
    push_notification_template = models.JSONField(null=True, blank=True)
    
    # Configurações de timing
    delay_hours = models.IntegerField(default=0)
    send_time_preference = models.CharField(max_length=20, default='immediate')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def execute_for_person(self, person):
        """Executa a automação para uma pessoa específica"""
        if not self.is_active:
            return False
            
        # Verificar se pessoa atende aos critérios
        if not self.person_matches_criteria(person):
            return False
            
        # Agendar envio com delay se necessário
        if self.delay_hours > 0:
            from django_q.tasks import schedule
            schedule(
                'core.tasks.execute_marketing_automation',
                self.id, person.id,
                schedule_type='O',  # Once
                next_run=timezone.now() + timedelta(hours=self.delay_hours)
            )
        else:
            self.send_communications(person)
            
        return True
    
    def person_matches_criteria(self, person):
        """Verifica se a pessoa atende aos critérios de segmentação"""
        if not self.target_segment:
            return True
            
        criteria = self.target_segment
        
        # Verificar idade
        if 'age_min' in criteria and person.age < criteria['age_min']:
            return False
        if 'age_max' in criteria and person.age > criteria['age_max']:
            return False
            
        # Verificar modalidades favoritas
        if 'favorite_modalities' in criteria:
            person_modalities = set(person.enhanced_profile.favorite_modalities.values_list('id', flat=True))
            required_modalities = set(criteria['favorite_modalities'])
            if not person_modalities.intersection(required_modalities):
                return False
                
        # Verificar loyalty score
        if 'loyalty_score_min' in criteria:
            if person.enhanced_profile.loyalty_score < criteria['loyalty_score_min']:
                return False
                
        return True
```

#### **Templates Dinâmicos:**
```python
class EmailTemplate(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=200)
    
    # Templates com variáveis dinâmicas
    html_content = models.TextField()
    text_content = models.TextField()
    
    # Personalização
    use_personalization = models.BooleanField(default=True)
    personalization_variables = models.JSONField(default=list)
    
    # A/B Testing
    variant_of = models.ForeignKey('self', null=True, blank=True)
    test_percentage = models.IntegerField(default=100)  # % que recebe esta variante
    
    # Métricas
    total_sent = models.IntegerField(default=0)
    total_opened = models.IntegerField(default=0)
    total_clicked = models.IntegerField(default=0)
    
    def render_for_person(self, person):
        """Renderiza template com dados personalizados"""
        context = {
            'person': person,
            'first_name': person.first_name,
            'full_name': person.get_full_name(),
            'loyalty_score': person.enhanced_profile.loyalty_score,
            'next_class': person.get_next_class(),
            'favorite_modality': person.enhanced_profile.favorite_modalities.first(),
            'gym_name': person.organization.name,
        }
        
        # Adicionar variáveis personalizadas
        for var in self.personalization_variables:
            if hasattr(person, var) or hasattr(person.enhanced_profile, var):
                context[var] = getattr(person, var, None) or getattr(person.enhanced_profile, var, None)
        
        from django.template import Template, Context
        html_template = Template(self.html_content)
        text_template = Template(self.text_content)
        subject_template = Template(self.subject)
        
        return {
            'subject': subject_template.render(Context(context)),
            'html_content': html_template.render(Context(context)),
            'text_content': text_template.render(Context(context)),
        }
```

---

## 📊 **3. ANÁLISES AVANÇADAS E BUSINESS INTELLIGENCE**

### **Dashboard Executivo com Previsões ML**

#### **Métricas de Negócio Avançadas:**
```python
class BusinessIntelligence:
    """Classe para cálculos de BI e previsões"""
    
    @staticmethod
    def calculate_kpis(organization, period='month'):
        """Calcula KPIs principais do negócio"""
        from datetime import datetime, timedelta
        from django.db.models import Avg, Sum, Count
        
        if period == 'month':
            start_date = datetime.now().replace(day=1)
        elif period == 'quarter':
            quarter_start = ((datetime.now().month - 1) // 3) * 3 + 1
            start_date = datetime.now().replace(month=quarter_start, day=1)
        else:  # year
            start_date = datetime.now().replace(month=1, day=1)
        
        end_date = datetime.now()
        
        # Receita e crescimento
        current_revenue = Payment.objects.filter(
            person__organization=organization,
            payment_date__gte=start_date,
            payment_date__lte=end_date,
            status='confirmed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Período anterior para comparação
        period_length = (end_date - start_date).days
        previous_start = start_date - timedelta(days=period_length)
        previous_end = start_date
        
        previous_revenue = Payment.objects.filter(
            person__organization=organization,
            payment_date__gte=previous_start,
            payment_date__lt=previous_end,
            status='confirmed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        revenue_growth = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
        
        # Membros ativos
        active_members = Person.objects.filter(
            organization=organization,
            enhanced_profile__last_activity__gte=start_date
        ).count()
        
        # Taxa de retenção
        retention_rate = BusinessIntelligence.calculate_retention_rate(organization, start_date, end_date)
        
        # Valor médio por cliente
        avg_customer_value = current_revenue / active_members if active_members > 0 else 0
        
        # Previsão de receita para próximo período
        predicted_revenue = BusinessIntelligence.predict_revenue(organization, period)
        
        # Churn rate
        churn_rate = BusinessIntelligence.calculate_churn_rate(organization, start_date, end_date)
        
        # Ocupação média das aulas
        avg_occupancy = BusinessIntelligence.calculate_avg_class_occupancy(organization, start_date, end_date)
        
        return {
            'current_revenue': current_revenue,
            'revenue_growth': revenue_growth,
            'active_members': active_members,
            'retention_rate': retention_rate,
            'avg_customer_value': avg_customer_value,
            'predicted_revenue': predicted_revenue,
            'churn_rate': churn_rate,
            'avg_occupancy': avg_occupancy,
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
        }
    
    @staticmethod
    def predict_revenue(organization, period='month'):
        """Previsão de receita usando ML"""
        import numpy as np
        from sklearn.linear_model import LinearRegression
        
        # Coletar dados históricos dos últimos 12 meses
        historical_data = []
        for i in range(12, 0, -1):
            month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            
            revenue = Payment.objects.filter(
                person__organization=organization,
                payment_date__gte=month_start,
                payment_date__lt=month_end,
                status='confirmed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            historical_data.append(revenue)
        
        if len(historical_data) < 3:
            return 0
        
        # Treinar modelo de regressão linear simples
        X = np.array(range(len(historical_data))).reshape(-1, 1)
        y = np.array(historical_data)
        
        model = LinearRegression()
        model.fit(X, y)
        
        # Prever próximo período
        next_period = len(historical_data)
        prediction = model.predict([[next_period]])[0]
        
        return max(prediction, 0)  # Não pode ser negativo
    
    @staticmethod
    def calculate_churn_rate(organization, start_date, end_date):
        """Calcula taxa de abandono no período"""
        # Membros que estavam ativos no início do período
        members_at_start = Person.objects.filter(
            organization=organization,
            enhanced_profile__last_activity__lt=start_date,
            created_at__lt=start_date
        ).count()
        
        # Membros que se tornaram inativos durante o período
        churned_members = Person.objects.filter(
            organization=organization,
            enhanced_profile__last_activity__lt=start_date,
            enhanced_profile__last_activity__gte=start_date - timedelta(days=30)
        ).count()
        
        return (churned_members / members_at_start * 100) if members_at_start > 0 else 0
```

#### **Relatórios Interativos:**
```python
class AdvancedReportsView(LoginRequiredMixin, View):
    """Views para relatórios avançados com gráficos interativos"""
    
    def get(self, request):
        organization = request.organization
        report_type = request.GET.get('type', 'overview')
        
        if report_type == 'overview':
            return self.overview_report(request, organization)
        elif report_type == 'revenue':
            return self.revenue_analysis(request, organization)
        elif report_type == 'members':
            return self.members_analysis(request, organization)
        elif report_type == 'classes':
            return self.classes_analysis(request, organization)
        
    def overview_report(self, request, organization):
        """Relatório geral com KPIs principais"""
        kpis = BusinessIntelligence.calculate_kpis(organization)
        
        # Dados para gráficos
        revenue_trend = self.get_revenue_trend(organization, months=6)
        member_growth = self.get_member_growth(organization, months=6)
        top_modalities = self.get_top_modalities(organization)
        
        context = {
            'kpis': kpis,
            'revenue_trend': revenue_trend,
            'member_growth': member_growth,
            'top_modalities': top_modalities,
            'charts_config': {
                'revenue_trend': {
                    'type': 'line',
                    'data': revenue_trend,
                    'options': {
                        'responsive': True,
                        'scales': {
                            'y': {
                                'beginAtZero': True,
                                'ticks': {
                                    'callback': 'function(value) { return "€" + value.toLocaleString(); }'
                                }
                            }
                        }
                    }
                },
                'member_growth': {
                    'type': 'bar',
                    'data': member_growth,
                    'options': {'responsive': True}
                }
            }
        }
        
        return render(request, 'core/reports/overview.html', context)
    
    def get_revenue_trend(self, organization, months=6):
        """Dados para gráfico de tendência de receita"""
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth
        
        revenue_by_month = Payment.objects.filter(
            person__organization=organization,
            payment_date__gte=datetime.now() - timedelta(days=30*months),
            status='confirmed'
        ).annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        return {
            'labels': [item['month'].strftime('%B %Y') for item in revenue_by_month],
            'datasets': [{
                'label': 'Receita Mensal',
                'data': [float(item['total']) for item in revenue_by_month],
                'borderColor': '#007bff',
                'backgroundColor': 'rgba(0, 123, 255, 0.1)',
                'tension': 0.4
            }]
        }
```

---

## 📱 **4. MOBILE APP PARA SÓCIOS**

### **Funcionalidades da App Mobile**

#### **Dashboard Personalizado:**
```javascript
// mobile/static/js/member-dashboard.js
class MemberDashboard {
    constructor() {
        this.member = null;
        this.notifications = [];
        this.init();
    }
    
    async init() {
        await this.loadMemberData();
        this.renderDashboard();
        this.setupNotifications();
        this.initPerformanceTracking();
    }
    
    async loadMemberData() {
        try {
            const response = await fetch('/api/mobile/member/dashboard/');
            this.member = await response.json();
        } catch (error) {
            console.error('Erro ao carregar dados do membro:', error);
        }
    }
    
    renderDashboard() {
        const container = document.getElementById('member-dashboard');
        
        container.innerHTML = `
            <div class="member-summary">
                <div class="avatar-section">
                    <img src="${this.member.avatar_url || '/static/img/default-avatar.png'}" 
                         class="member-avatar">
                    <h2>${this.member.first_name}</h2>
                    <p class="member-status ${this.member.status.toLowerCase()}">
                        ${this.member.status_display}
                    </p>
                </div>
                
                <div class="quick-stats">
                    <div class="stat-card">
                        <span class="stat-value">${this.member.this_month_visits}</span>
                        <span class="stat-label">Visitas este Mês</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${this.member.loyalty_score}/100</span>
                        <span class="stat-label">Score Fidelização</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${this.member.next_payment_days}</span>
                        <span class="stat-label">Dias p/ Pagamento</span>
                    </div>
                </div>
            </div>
            
            <div class="upcoming-classes">
                <h3>Próximas Aulas</h3>
                <div class="classes-list">
                    ${this.renderUpcomingClasses()}
                </div>
            </div>
            
            <div class="quick-actions">
                <button class="action-btn primary" onclick="this.openClassSchedule()">
                    📅 Ver Horários
                </button>
                <button class="action-btn secondary" onclick="this.openQRScanner()">
                    📱 Check-in QR
                </button>
                <button class="action-btn secondary" onclick="this.openPayments()">
                    💳 Pagamentos
                </button>
            </div>
        `;
    }
    
    renderUpcomingClasses() {
        return this.member.upcoming_classes.map(cls => `
            <div class="class-item">
                <div class="class-time">
                    ${new Date(cls.starts_at).toLocaleDateString('pt-PT')} às 
                    ${new Date(cls.starts_at).toLocaleTimeString('pt-PT', {hour: '2-digit', minute: '2-digit'})}
                </div>
                <div class="class-info">
                    <h4>${cls.modality.name}</h4>
                    <p>${cls.instructor.name} • ${cls.resource.name}</p>
                </div>
                <button class="btn-cancel" onclick="this.cancelBooking(${cls.id})">
                    Cancelar
                </button>
            </div>
        `).join('');
    }
    
    async cancelBooking(classId) {
        if (!confirm('Tem certeza que deseja cancelar esta reserva?')) return;
        
        try {
            const response = await fetch(`/api/mobile/bookings/${classId}/cancel/`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            if (response.ok) {
                this.showNotification('Reserva cancelada com sucesso!', 'success');
                this.loadMemberData(); // Recarregar dados
                this.renderDashboard();
            }
        } catch (error) {
            this.showNotification('Erro ao cancelar reserva', 'error');
        }
    }
    
    initPerformanceTracking() {
        // Tracking de performance da app
        const startTime = performance.now();
        
        window.addEventListener('load', () => {
            const loadTime = performance.now() - startTime;
            
            // Enviar métricas para o backend
            fetch('/api/mobile/analytics/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    event: 'dashboard_load',
                    load_time: loadTime,
                    user_agent: navigator.userAgent,
                    timestamp: new Date().toISOString()
                })
            });
        });
    }
}
```

#### **Sistema de Reservas Mobile:**
```javascript
// mobile/static/js/mobile-reservations.js
class MobileReservations {
    constructor() {
        this.selectedDate = new Date();
        this.selectedClass = null;
        this.init();
    }
    
    init() {
        this.loadSchedule();
        this.setupDatePicker();
        this.setupFilters();
    }
    
    async loadSchedule() {
        const dateStr = this.selectedDate.toISOString().split('T')[0];
        
        try {
            const response = await fetch(`/api/mobile/schedule/?date=${dateStr}`);
            const schedule = await response.json();
            this.renderSchedule(schedule);
        } catch (error) {
            console.error('Erro ao carregar horários:', error);
        }
    }
    
    renderSchedule(schedule) {
        const container = document.getElementById('mobile-schedule');
        
        const groupedByTime = schedule.reduce((acc, cls) => {
            const time = new Date(cls.starts_at).toLocaleTimeString('pt-PT', {
                hour: '2-digit', 
                minute: '2-digit'
            });
            
            if (!acc[time]) acc[time] = [];
            acc[time].push(cls);
            return acc;
        }, {});
        
        container.innerHTML = Object.entries(groupedByTime)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([time, classes]) => `
                <div class="time-slot">
                    <div class="time-header">${time}</div>
                    <div class="classes-grid">
                        ${classes.map(cls => this.renderClassCard(cls)).join('')}
                    </div>
                </div>
            `).join('');
    }
    
    renderClassCard(cls) {
        const isBooked = cls.user_booking_status === 'confirmed';
        const isFull = cls.confirmed_bookings >= cls.max_capacity;
        const isWaitingList = cls.user_booking_status === 'waiting';
        
        let statusClass = '';
        let actionText = 'Reservar';
        let actionClass = 'btn-reserve';
        
        if (isBooked) {
            statusClass = 'booked';
            actionText = 'Cancelar';
            actionClass = 'btn-cancel';
        } else if (isFull) {
            statusClass = 'full';
            actionText = 'Lista Espera';
            actionClass = 'btn-waiting';
        } else if (isWaitingList) {
            statusClass = 'waiting';
            actionText = 'Na Lista';
            actionClass = 'btn-waiting';
        }
        
        return `
            <div class="class-card ${statusClass}" data-class-id="${cls.id}">
                <div class="class-header">
                    <h4>${cls.modality.name}</h4>
                    <span class="capacity">
                        ${cls.confirmed_bookings}/${cls.max_capacity}
                    </span>
                </div>
                
                <div class="class-details">
                    <p class="instructor">👨‍🏫 ${cls.instructor.name}</p>
                    <p class="location">📍 ${cls.resource.name}</p>
                    <p class="duration">⏱️ ${cls.duration_minutes}min</p>
                </div>
                
                <button class="class-action ${actionClass}" 
                        onclick="this.handleClassAction(${cls.id}, '${actionText.toLowerCase()}')">
                    ${actionText}
                </button>
                
                ${isWaitingList ? `
                    <div class="waiting-info">
                        <small>Posição: ${cls.waiting_list_position}º</small>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    async handleClassAction(classId, action) {
        const endpoints = {
            'reservar': '/api/mobile/bookings/create/',
            'cancelar': '/api/mobile/bookings/cancel/',
            'lista espera': '/api/mobile/waiting-list/join/',
        };
        
        const endpoint = endpoints[action];
        if (!endpoint) return;
        
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    class_id: classId,
                    notification_preferences: {
                        push: true,
                        sms: false,
                        email: true
                    }
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showNotification(result.message, 'success');
                this.loadSchedule(); // Recarregar horários
            } else {
                this.showNotification(result.error, 'error');
            }
        } catch (error) {
            this.showNotification('Erro de conexão', 'error');
        }
    }
}
```

---

## 🔒 **5. CONFORMIDADE RGPD**

### **Sistema de Gestão de Consentimentos**

#### **Modelos para Compliance:**
```python
class GDPRConsent(models.Model):
    CONSENT_TYPES = [
        ('essential', 'Funcionalidades Essenciais'),
        ('marketing', 'Marketing e Comunicação'),
        ('analytics', 'Análise de Comportamento'),
        ('data_sharing', 'Partilha de Dados'),
        ('automated_decisions', 'Decisões Automatizadas'),
    ]
    
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    consent_type = models.CharField(max_length=20, choices=CONSENT_TYPES)
    granted = models.BooleanField()
    granted_date = models.DateTimeField(auto_now_add=True)
    withdrawn_date = models.DateTimeField(null=True, blank=True)
    
    # Contexto do consentimento
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    consent_method = models.CharField(max_length=50)  # web, mobile, paper, etc.
    
    # Auditoria
    version = models.CharField(max_length=10, default='1.0')  # Versão dos termos
    legal_basis = models.CharField(max_length=100)
    
    class Meta:
        unique_together = ['person', 'consent_type']
        indexes = [
            models.Index(fields=['person', 'consent_type']),
            models.Index(fields=['granted_date']),
        ]
    
    def withdraw(self):
        """Retirar consentimento"""
        self.granted = False
        self.withdrawn_date = timezone.now()
        self.save()
        
        # Trigger para limpar dados relacionados se necessário
        from django_q.tasks import async_task
        async_task('core.gdpr_tasks.process_consent_withdrawal', self.id)

class DataProcessingActivity(models.Model):
    """Registo de atividades de processamento de dados (Art. 30 RGPD)"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Categorias de dados
    data_categories = models.JSONField(default=list)  # ['personal', 'financial', 'health', etc.]
    data_subjects = models.JSONField(default=list)    # ['customers', 'employees', 'suppliers']
    
    # Finalidades
    purposes = models.JSONField(default=list)
    legal_basis = models.CharField(max_length=100)
    
    # Retenção
    retention_period = models.CharField(max_length=100)
    deletion_criteria = models.TextField()
    
    # Destinatários
    recipients = models.JSONField(default=list)
    third_country_transfers = models.JSONField(default=list)
    
    # Medidas de segurança
    security_measures = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class DataSubjectRequest(models.Model):
    """Pedidos dos titulares de dados (Arts. 15-22 RGPD)"""
    REQUEST_TYPES = [
        ('access', 'Acesso aos Dados (Art. 15)'),
        ('rectification', 'Retificação (Art. 16)'),
        ('erasure', 'Apagamento (Art. 17)'),
        ('restriction', 'Limitação (Art. 18)'),
        ('portability', 'Portabilidade (Art. 20)'),
        ('objection', 'Oposição (Art. 21)'),
    ]
    
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    description = models.TextField()
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('submitted', 'Submetido'),
        ('acknowledged', 'Reconhecido'),
        ('processing', 'Em Processamento'),
        ('completed', 'Concluído'),
        ('rejected', 'Rejeitado'),
    ], default='submitted')
    
    # Resposta
    response = models.TextField(blank=True)
    response_attachments = models.JSONField(default=list)
    
    # Auditoria
    processed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    
    def acknowledge(self, user):
        """Reconhecer receção do pedido"""
        self.acknowledged_at = timezone.now()
        self.status = 'acknowledged'
        self.processed_by = user
        self.save()
        
        # Enviar email de confirmação
        from core.gdpr_tasks import send_acknowledgment_email
        send_acknowledgment_email.delay(self.id)
    
    def complete(self, response, attachments=None):
        """Concluir processamento do pedido"""
        self.completed_at = timezone.now()
        self.status = 'completed'
        self.response = response
        if attachments:
            self.response_attachments = attachments
        self.save()
        
        # Enviar resposta ao titular
        from core.gdpr_tasks import send_completion_email
        send_completion_email.delay(self.id)
```

---

## 📈 **CRONOGRAMA DE IMPLEMENTAÇÃO DETALHADO**

### **FASE 1 - Fundação CRM (Meses 1-2)**

#### **Semana 1-2: Modelos e Base de Dados**
- [ ] Criar modelos `EnhancedPersonProfile`
- [ ] Criar modelos `CustomerInteraction`
- [ ] Criar modelos `MarketingAutomation`
- [ ] Executar migrações
- [ ] Popular dados históricos

#### **Semana 3-4: APIs CRM**
- [ ] Implementar APIs mobile CRM
- [ ] Criar endpoints de análise
- [ ] Implementar cálculo de loyalty score
- [ ] Testes de performance

#### **Semana 5-6: Interface Web CRM**
- [ ] Dashboard CRM web
- [ ] Gestão de campanhas
- [ ] Relatórios básicos
- [ ] Testes de utilizador

#### **Semana 7-8: RGPD Base**
- [ ] Modelos de consentimento
- [ ] Sistema de auditoria
- [ ] Políticas de retenção
- [ ] Documentação compliance

---

### **FASE 2 - Mobile App e Reservas (Meses 2-3)**

#### **Semana 9-10: PWA Avançada**
- [ ] Dashboard mobile personalizado
- [ ] Sistema de reservas mobile
- [ ] QR Code check-in
- [ ] Notificações push

#### **Semana 11-12: Lista de Espera**
- [ ] Sistema automático de listas
- [ ] Notificações em tempo real
- [ ] Gestão de prioridades
- [ ] Métricas de eficiência

#### **Semana 13-14: Pagamentos Mobile**
- [ ] Integração Stripe/PayPal
- [ ] Pagamentos recorrentes
- [ ] Histórico de pagamentos
- [ ] Faturas digitais

#### **Semana 15-16: Offline Sync**
- [ ] Service Workers avançados
- [ ] Cache inteligente
- [ ] Sync em background
- [ ] Resolução de conflitos

---

### **FASE 3 - Marketing e Analytics (Meses 3-4)**

#### **Semana 17-18: Automação Marketing**
- [ ] Engine de campanhas
- [ ] Templates dinâmicos
- [ ] A/B Testing
- [ ] Segmentação avançada

#### **Semana 19-20: Relatórios ML**
- [ ] Algoritmos de previsão
- [ ] Análise de churn
- [ ] Dashboards interativos
- [ ] Exportação automática

#### **Semana 21-22: Integrações**
- [ ] Mailchimp API
- [ ] SMS Gateway
- [ ] WhatsApp Business
- [ ] Google Analytics

#### **Semana 23-24: Portal Instrutor**
- [ ] Dashboard instrutor mobile
- [ ] Gestão de comissões
- [ ] Comunicação com alunos
- [ ] Métricas de performance

---

### **FASE 4 - Compliance e Otimização (Meses 4-5)**

#### **Semana 25-26: RGPD Completo**
- [ ] Interface gestão consentimentos
- [ ] Exportação de dados
- [ ] Direito ao esquecimento
- [ ] Auditoria automática

#### **Semana 27-28: Segurança Avançada**
- [ ] Encriptação end-to-end
- [ ] Logs de auditoria
- [ ] Detecção de anomalias
- [ ] Backup automático

#### **Semana 29-30: Performance**
- [ ] Otimização de queries
- [ ] Cache Redis avançado
- [ ] CDN para assets
- [ ] Monitoring completo

#### **Semana 31-32: Testes e Deploy**
- [ ] Testes de carga
- [ ] Testes de segurança
- [ ] Deploy em produção
- [ ] Documentação final

---

## 💰 **ANÁLISE DE ROI E BENEFÍCIOS**

### **Investimento Estimado:**
- **Desenvolvimento**: 4-5 meses × €8.000/mês = €32.000-€40.000
- **Infraestrutura**: €200/mês (serviços cloud)
- **Licenças/APIs**: €150/mês (Mailchimp, SMS, etc.)
- **Manutenção**: €2.000/mês

### **Retorno Esperado Anual:**
- **Redução custos administrativos**: €15.000/ano
- **Aumento retenção clientes (+30%)**: €25.000/ano
- **Automação marketing (+25% receita)**: €20.000/ano
- **Otimização operacional**: €10.000/ano
- **Total**: €70.000/ano

### **ROI**: 175% no primeiro ano

---

## 🎯 **MÉTRICAS DE SUCESSO**

### **KPIs Técnicos:**
- **Tempo de resposta APIs**: <200ms
- **Uptime**: >99.5%
- **App rating**: >4.5/5
- **Adoption rate**: >80% dos sócios

### **KPIs de Negócio:**
- **Retenção de clientes**: +30%
- **Eficiência operacional**: +40%
- **Satisfação do cliente**: >4.5/5
- **Revenue per customer**: +25%

### **KPIs de Compliance:**
- **RGPD compliance**: 100%
- **Tempo resposta pedidos**: <72h
- **Breach incidents**: 0
- **Audit score**: >95%

---

## 🚀 **CONCLUSÃO**

Este plano transformará o ACR Gestão numa plataforma completa de gestão de ginásios com:

✅ **CRM avançado** com automação inteligente
✅ **Mobile-first experience** para todos os utilizadores  
✅ **Analytics preditivas** com machine learning
✅ **Marketing automation** personalizado
✅ **Compliance RGPD** 100% automático
✅ **ROI comprovado** de 175% no primeiro ano

A implementação faseada garante **entrega contínua de valor** e **risco minimizado**, posicionando o ACR Gestão como **líder de mercado** na digitalização de ginásios em Portugal.
