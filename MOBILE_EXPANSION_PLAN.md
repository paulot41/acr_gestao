# PLANO DE EXPANSÃO MOBILE - ACR GESTÃO
# =====================================

## 📱 ESTRATÉGIA RECOMENDADA: Progressive Web App (PWA)

### Atualizações recentes

- Substituição de blocos `except Exception` por exceções específicas com logging.
- Remoção da criação automática de organização em `get_current_organization`.
- Consolidação do middleware de multi-tenancy.
- Cálculos financeiros com `Decimal`.
- Migração de `unique_together` para `UniqueConstraint`.
- Limpeza de imports desnecessários.
- Inclusão de testes automatizados para modelos e middleware.

### VANTAGENS:
- Aproveita 90% do código atual
- Instalável como app nativa
- Funciona offline
- Push notifications
- Desenvolvimento mais rápido

### ESTRUTURA PROPOSTA:

```
acr_gestao/
├── core/
│   ├── templates/
│   │   ├── mobile/          # Novos templates mobile
│   │   │   ├── base_mobile.html
│   │   │   ├── dashboard_mobile.html  
│   │   │   ├── gantt_mobile.html
│   │   │   └── client_list_mobile.html
│   │   └── core/           # Templates desktop atuais
│   ├── static/
│   │   ├── mobile/         # CSS/JS específico mobile
│   │   │   ├── css/mobile.css
│   │   │   ├── js/mobile.js
│   │   │   └── manifest.json (PWA)
│   │   └── css/           # Estilos desktop atuais
│   └── views/
│       ├── mobile_views.py # Views otimizadas mobile
│       └── api_views.py    # APIs expandidas
```

## 🔧 IMPLEMENTAÇÃO TÉCNICA:

### 1. DETECÇÃO DE DISPOSITIVO:
```python
def mobile_dashboard(request):
    if request.user_agent.is_mobile:
        return render(request, 'mobile/dashboard_mobile.html', context)
    else:
        return render(request, 'core/dashboard.html', context)
```

### 2. APIs MOBILE OTIMIZADAS:
```python
class MobilePersonViewSet(PersonViewSet):
    """APIs otimizadas para mobile com menos dados"""
    serializer_class = MobilePersonSerializer
    pagination_class = MobilePagination
```

### 3. PWA CONFIGURATION:
```json
{
  "name": "ACR Gestão",
  "short_name": "ACR",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0d6efd",
  "theme_color": "#0d6efd"
}
```

## 📊 FUNCIONALIDADES MOBILE PRIORITÁRIAS:

### FASE MOBILE 1: (2-3 semanas)
- [ ] Dashboard mobile responsivo
- [ ] Lista de clientes touch-friendly
- [ ] Gantt simplificado para mobile
- [ ] PWA básica (instalável)

### FASE MOBILE 2: (3-4 semanas)  
- [ ] Check-in por QR Code
- [ ] Notificações push
- [ ] Sincronização offline
- [ ] Câmara para fotos de clientes

### FASE MOBILE 3: (4-5 semanas)
- [ ] App nativa (React Native/Flutter)
- [ ] Geolocalização
- [ ] Integração calendário nativo
- [ ] Biometria para login

## 🎯 ROADMAP MOBILE:

### CURTO PRAZO (1-2 meses):
1. Interface mobile responsiva
2. PWA funcional
3. APIs mobile otimizadas

### MÉDIO PRAZO (3-4 meses):
1. App nativa iOS/Android
2. Funcionalidades offline
3. Integração sensores móveis

### LONGO PRAZO (6+ meses):
1. AI/ML para previsões
2. Wearables integration
3. IoT gym equipment

## 💡 BENEFÍCIOS ESPECÍFICOS DO MOBILE:

### PARA CLIENTES:
- Check-in automático por GPS
- Reservas rápidas via app
- Notificações de aulas
- Progresso fitness tracking

### PARA INSTRUTORES:
- Gestão de aulas via mobile
- Check-in de alunos por QR
- Calendário sincronizado
- Comissões em tempo real

### PARA ADMINISTRAÇÃO:
- Gestão remota
- Relatórios em tempo real
- Notificações de emergência
- Backup e sync automático

## 🔥 VANTAGEM COMPETITIVA:

A arquitetura atual (Django + API REST) é PERFEITA para mobile porque:
- ✅ Backend robusto já implementado
- ✅ APIs documentadas e testadas  
- ✅ Multi-tenancy funcional
- ✅ Sistema de permissões completo
- ✅ Sincronização automática garantida

## 🚀 **EXPANSÃO PARA FUNCIONALIDADES CRM E AVANÇADAS**

### 📊 **CRM INTEGRADO NO MOBILE**

#### **Dashboard CRM Mobile:**
```
mobile_app/
├── templates/mobile/
│   ├── crm/
│   │   ├── member_profile.html      # Perfil completo do sócio
│   │   ├── membership_history.html  # Histórico de mensalidades
│   │   ├── communication_log.html   # Log de comunicações
│   │   └── loyalty_dashboard.html   # Score de fidelização
│   └── analytics/
│       ├── attendance_stats.html    # Estatísticas de presenças
│       ├── revenue_reports.html     # Relatórios de receita
│       └── churn_analysis.html      # Análise de abandono
```

#### **APIs CRM Mobile-Optimized:**
```python
class MobileCRMAPI(APIView):
    """APIs otimizadas para CRM mobile"""
    
    def get_member_summary(self, request, member_id):
        """Resumo do sócio para mobile"""
        return {
            'basic_info': member.get_mobile_summary(),
            'membership_status': member.get_current_status(),
            'loyalty_score': member.calculate_loyalty_score(),
            'recent_activities': member.get_recent_activities(limit=5)
        }
    
    def get_communication_feed(self, request, member_id):
        """Feed de comunicações otimizado para mobile"""
        return CommunicationLog.objects.filter(
            person_id=member_id
        ).select_related('campaign').order_by('-sent_date')[:20]

class MobileAnalyticsAPI(APIView):
    """Analytics específicas para mobile"""
    
    def get_dashboard_metrics(self, request):
        """Métricas principais para dashboard mobile"""
        return {
            'today_revenue': calculate_today_revenue(),
            'active_members': get_active_members_count(),
            'class_occupancy': get_current_occupancy_rate(),
            'trending_modalities': get_trending_modalities()
        }
```

---

### 📱 **RESERVAS AVANÇADAS MOBILE**

#### **Sistema de Listas de Espera:**
```html
<!-- templates/mobile/reservations/waiting_list.html -->
<div class="waiting-list-card">
    <h3>Lista de Espera - Pilates</h3>
    <p>Posição: <strong>3º</strong> na fila</p>
    <p>Estimativa: <span class="eta">15 min</span></p>
    
    <div class="notification-settings">
        <label>
            <input type="checkbox" checked> Notificar por push
        </label>
        <label>
            <input type="checkbox"> Notificar por SMS
        </label>
    </div>
    
    <button class="btn-cancel-waiting">Sair da Lista</button>
</div>
```

#### **Auto Check-in via QR Code:**
```javascript
// mobile/static/js/qr-checkin.js
class QRCheckIn {
    constructor() {
        this.scanner = new QrScanner(video, result => this.onQRDetected(result));
    }
    
    async onQRDetected(qrCode) {
        try {
            const response = await fetch('/api/mobile/checkin/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    qr_code: qrCode,
                    location: await this.getCurrentLocation()
                })
            });
            
            if (response.ok) {
                this.showSuccessMessage('Check-in realizado com sucesso!');
                this.updateUI();
            }
        } catch (error) {
            this.showErrorMessage('Erro no check-in. Tente novamente.');
        }
    }
}
```

---

### 📧 **MARKETING AUTOMATION MOBILE**

#### **Templates de Campanha Mobile-First:**
```python
# marketing/models.py
class MobileEmailTemplate(models.Model):
    organization = models.ForeignKey(Organization)
    name = models.CharField(max_length=100)
    subject_template = models.CharField(max_length=200)
    
    # Templates otimizados para mobile
    mobile_html_template = models.TextField()
    mobile_text_template = models.TextField()
    
    # Configurações de design mobile
    primary_color = models.CharField(max_length=7, default='#007bff')
    secondary_color = models.CharField(max_length=7, default='#6c757d')
    logo_url = models.URLField(blank=True)
    
    # Automação
    trigger_type = models.CharField(choices=TriggerType.choices)
    trigger_delay_hours = models.IntegerField(default=0)
    
class AutomationRule(models.Model):
    organization = models.ForeignKey(Organization)
    name = models.CharField(max_length=100)
    
    # Condições de ativação
    trigger_event = models.CharField(choices=EventType.choices)
    target_segment = models.JSONField()  # Critérios de segmentação
    
    # Ações a executar
    email_template = models.ForeignKey(MobileEmailTemplate, null=True)
    sms_template = models.ForeignKey(SMSTemplate, null=True)
    push_notification = models.JSONField(null=True)
    
    is_active = models.BooleanField(default=True)
```

#### **Campaign Dashboard Mobile:**
```html
<!-- templates/mobile/marketing/campaigns.html -->
<div class="campaign-dashboard">
    <div class="metrics-row">
        <div class="metric-card">
            <h4>Emails Enviados</h4>
            <span class="metric-value">1,247</span>
            <span class="metric-change positive">+12%</span>
        </div>
        
        <div class="metric-card">
            <h4>Taxa de Abertura</h4>
            <span class="metric-value">24.5%</span>
            <span class="metric-change positive">+3.2%</span>
        </div>
    </div>
    
    <div class="active-campaigns">
        <h3>Campanhas Ativas</h3>
        <div class="campaign-item">
            <h4>Boas-vindas Setembro</h4>
            <p>23 novos sócios contactados</p>
            <div class="progress-bar">
                <div class="progress" style="width: 78%"></div>
            </div>
        </div>
    </div>
</div>
```

---

### 📊 **RELATÓRIOS AVANÇADOS MOBILE**

#### **Charts Interativos Mobile:**
```javascript
// mobile/static/js/mobile-charts.js
class MobileCharts {
    constructor() {
        this.charts = {};
        this.initCharts();
    }
    
    initCharts() {
        // Gráfico de receitas com Chart.js otimizado para mobile
        this.charts.revenue = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.getLastMonths(),
                datasets: [{
                    label: 'Receita Mensal',
                    data: this.getRevenueData(),
                    borderColor: '#007bff',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false  // Economia de espaço no mobile
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: value => '€' + value.toLocaleString()
                        }
                    }
                }
            }
        });
        
        // Heatmap de ocupação das aulas
        this.initOccupancyHeatmap();
    }
    
    initOccupancyHeatmap() {
        const heatmapData = this.getOccupancyData();
        
        // Usar biblioteca específica para mobile
        this.charts.occupancy = new MobileHeatmap('#occupancy-chart', {
            data: heatmapData,
            colorScale: ['#e3f2fd', '#1976d2'],
            responsive: true,
            touchEnabled: true
        });
    }
}
```

---

### 👨‍🏫 **PORTAL DE INSTRUTORES MOBILE**

#### **Dashboard do Instrutor:**
```html
<!-- templates/mobile/instructor/dashboard.html -->
<div class="instructor-mobile-dashboard">
    <div class="instructor-summary">
        <img src="{{ instructor.avatar_url }}" class="instructor-avatar">
        <h2>{{ instructor.get_full_name }}</h2>
        <p class="instructor-rating">
            ⭐ {{ instructor.rating|floatformat:1 }} 
            ({{ instructor.total_reviews }} avaliações)
        </p>
    </div>
    
    <div class="quick-stats">
        <div class="stat-item">
            <span class="stat-value">{{ today_classes }}</span>
            <span class="stat-label">Aulas Hoje</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">€{{ month_commission|floatformat:0 }}</span>
            <span class="stat-label">Comissões</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">{{ active_students }}</span>
            <span class="stat-label">Alunos Ativos</span>
        </div>
    </div>
    
    <div class="upcoming-classes">
        <h3>Próximas Aulas</h3>
        {% for class in upcoming_classes %}
        <div class="class-card">
            <div class="class-time">{{ class.starts_at|time:"H:i" }}</div>
            <div class="class-info">
                <h4>{{ class.modality.name }}</h4>
                <p>{{ class.resource.name }}</p>
                <span class="attendance-count">
                    {{ class.confirmed_bookings }}/{{ class.max_capacity }}
                </span>
            </div>
            <button class="btn-take-attendance">Presenças</button>
        </div>
        {% endfor %}
    </div>
</div>
```

#### **Registo de Presenças Mobile:**
```javascript
// mobile/static/js/attendance-mobile.js
class MobileAttendance {
    constructor(classId) {
        this.classId = classId;
        this.students = [];
        this.initAttendanceList();
    }
    
    initAttendanceList() {
        const container = document.getElementById('attendance-list');
        
        this.students.forEach(student => {
            const studentRow = this.createStudentRow(student);
            container.appendChild(studentRow);
        });
        
        // Adicionar funcionalidade de swipe para marcar presença
        this.initSwipeGestures();
    }
    
    createStudentRow(student) {
        const row = document.createElement('div');
        row.className = 'student-row';
        row.innerHTML = `
            <div class="student-info">
                <img src="${student.avatar}" class="student-avatar">
                <span class="student-name">${student.name}</span>
            </div>
            <div class="attendance-actions">
                <button class="btn-present ${student.is_present ? 'active' : ''}"
                        onclick="this.markPresent('${student.id}')">
                    ✓ Presente
                </button>
                <button class="btn-absent ${student.is_absent ? 'active' : ''}"
                        onclick="this.markAbsent('${student.id}')">
                    ✗ Ausente
                </button>
            </div>
        `;
        return row;
    }
    
    async saveAttendance() {
        const attendanceData = this.students.map(student => ({
            student_id: student.id,
            status: student.attendance_status,
            notes: student.notes || ''
        }));
        
        try {
            const response = await fetch(`/api/mobile/attendance/${this.classId}/`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({attendance: attendanceData})
            });
            
            if (response.ok) {
                this.showSuccessMessage('Presenças guardadas com sucesso!');
            }
        } catch (error) {
            this.showErrorMessage('Erro ao guardar presenças');
        }
    }
}
```

---

### 🔒 **CONFORMIDADE RGPD MOBILE**

#### **Gestão de Consentimentos Mobile:**
```html
<!-- templates/mobile/gdpr/consent_management.html -->
<div class="gdpr-consent-mobile">
    <h2>Gestão de Privacidade</h2>
    
    <div class="consent-categories">
        <div class="consent-item">
            <div class="consent-header">
                <h3>Marketing e Comunicação</h3>
                <label class="toggle-switch">
                    <input type="checkbox" {{ user.marketing_consent|yesno:"checked," }}>
                    <span class="slider"></span>
                </label>
            </div>
            <p>Receber emails promocionais, SMS e notificações push sobre ofertas especiais.</p>
        </div>
        
        <div class="consent-item">
            <div class="consent-header">
                <h3>Análise de Comportamento</h3>
                <label class="toggle-switch">
                    <input type="checkbox" {{ user.analytics_consent|yesno:"checked," }}>
                    <span class="slider"></span>
                </label>
            </div>
            <p>Permitir análise dos seus padrões de uso para melhorar a experiência.</p>
        </div>
    </div>
    
    <div class="data-rights">
        <h3>Os Seus Direitos</h3>
        <button class="btn-secondary" onclick="requestDataExport()">
            📄 Exportar os Meus Dados
        </button>
        <button class="btn-secondary" onclick="requestDataDeletion()">
            🗑️ Eliminar os Meus Dados
        </button>
        <button class="btn-secondary" onclick="viewDataUsage()">
            👁️ Ver Como os Dados São Usados
        </button>
    </div>
</div>
```

#### **Audit Trail Mobile:**
```python
# gdpr/mobile_views.py
class MobileGDPRView(LoginRequiredMixin, View):
    """Views RGPD otimizadas para mobile"""
    
    def get_data_usage_summary(self, request):
        """Resumo de uso de dados para mobile"""
        user_data = {
            'last_login': request.user.last_login,
            'data_collected': self.get_collected_data_summary(request.user),
            'sharing_partners': self.get_data_sharing_info(),
            'retention_period': self.get_retention_period(),
            'access_log': DataAccessLog.objects.filter(
                person=request.user.person
            ).order_by('-timestamp')[:10]
        }
        return JsonResponse(user_data)
    
    def export_user_data(self, request):
        """Exportação de dados em formato mobile-friendly"""
        export_data = GDPRExporter.export_user_data(
            request.user,
            format='mobile_json'  # Formato otimizado para mobile
        )
        
        # Enviar por email com link de download
        send_data_export_email.delay(
            user_id=request.user.id,
            export_data=export_data
        )
        
        return JsonResponse({
            'message': 'Os seus dados serão enviados por email em alguns minutos.',
            'status': 'processing'
        })
```

---

## 📊 **ARQUITETURA TÉCNICA EXPANDIDA**

### **Backend APIs Mobile-First:**
```python
# mobile/api_views.py
class MobileAPIViewSet(viewsets.ModelViewSet):
    """Base ViewSet otimizada para mobile"""
    
    def get_serializer_class(self):
        """Usar serializers específicos para mobile"""
        if self.action in ['list', 'retrieve']:
            return self.mobile_serializer_class
        return self.desktop_serializer_class
    
    def get_queryset(self):
        """Queries otimizadas para mobile"""
        queryset = super().get_queryset()
        
        # Menos dados por página no mobile
        if self.request.user_agent.is_mobile:
            self.pagination_class.page_size = 10
        
        return queryset.select_related(*self.mobile_select_related)

class MobilePersonViewSet(MobileAPIViewSet):
    """Gestão de pessoas otimizada para mobile"""
    mobile_serializer_class = MobilePersonSerializer
    desktop_serializer_class = PersonSerializer
    mobile_select_related = ['organization', 'membership']
    
    @action(detail=True, methods=['get'])
    def mobile_summary(self, request, pk=None):
        """Resumo otimizado para tela pequena"""
        person = self.get_object()
        return Response({
            'basic_info': person.get_mobile_basic_info(),
            'status': person.get_status_summary(),
            'next_class': person.get_next_class(),
            'notifications': person.get_pending_notifications()[:3]
        })
```

### **PWA Service Worker Expandido:**
```javascript
// mobile/static/sw.js
const CACHE_NAME = 'acr-gestao-mobile-v3.0';
const OFFLINE_PAGES = [
    '/mobile/',
    '/mobile/offline/',
    '/mobile/reservations/offline/',
    '/mobile/profile/'
];

self.addEventListener('fetch', event => {
    // Estratégias de cache específicas por tipo de conteúdo
    if (event.request.url.includes('/api/mobile/')) {
        // API calls: Network first, cache fallback
        event.respondWith(networkFirstStrategy(event.request));
    } else if (event.request.url.includes('/static/mobile/')) {
        // Assets estáticos: Cache first
        event.respondWith(cacheFirstStrategy(event.request));
    } else if (event.request.url.includes('/mobile/')) {
        // Páginas mobile: Stale while revalidate
        event.respondWith(staleWhileRevalidateStrategy(event.request));
    }
});

// Background sync para ações offline
self.addEventListener('sync', event => {
    if (event.tag === 'background-attendance') {
        event.waitUntil(syncAttendanceData());
    } else if (event.tag === 'background-reservations') {
        event.waitUntil(syncReservationData());
    }
});

// Push notifications
self.addEventListener('push', event => {
    const options = {
        body: event.data.text(),
        icon: '/static/mobile/icons/icon-192x192.png',
        badge: '/static/mobile/icons/badge-72x72.png',
        actions: [
            {action: 'view', title: 'Ver Detalhes'},
            {action: 'dismiss', title: 'Dispensar'}
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('ACR Gestão', options)
    );
});
```

---

## 🎯 **ROADMAP DE IMPLEMENTAÇÃO MOBILE EXPANDIDO**

### **FASE 1 (Mês 1-2): Fundação Mobile + CRM**
- ✅ PWA base funcional
- ✅ Sistema de autenticação mobile
- ✅ Dashboard CRM mobile
- ✅ APIs mobile-optimized

### **FASE 2 (Mês 2-3): Reservas Avançadas**
- ✅ Lista de espera automática
- ✅ QR Code check-in
- ✅ Push notifications
- ✅ Offline sync

### **FASE 3 (Mês 3-4): Marketing & Analytics**
- ✅ Campaign management mobile
- ✅ Relatórios interativos
- ✅ Dashboard de métricas
- ✅ Exportação de dados

### **FASE 4 (Mês 4-5): Portal Instrutor + RGPD**
- ✅ Dashboard instrutor mobile
- ✅ Registo de presenças touch
- ✅ Conformidade RGPD completa
- ✅ Auditoria e compliance

---

## 💰 **ESTIMATIVA DE IMPACTO FINANCEIRO**

### **ROI Esperado:**
- **Redução custos operacionais**: 40% (automação de processos)
- **Aumento retenção clientes**: 35% (experiência mobile)
- **Eficiência marketing**: 50% (automação de campanhas)
- **Compliance legal**: 100% (RGPD automático)

### **Métricas de Sucesso:**
- **App downloads**: 80% dos sócios ativos
- **Engagement rate**: >60% uso semanal
- **Customer satisfaction**: >4.5/5 rating
- **Time to market**: 5 meses para implementação completa
