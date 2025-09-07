from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import JsonResponse
from django.db.models import Count, Q  # Importar funções de agregação corretas
from django.utils import timezone
from datetime import timedelta
from . import models


class OrgScopedAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        org = getattr(request, "organization", None)
        if org:
            return qs.filter(organization=org)
        return qs

    def save_model(self, request, obj, form, change):
        if not getattr(obj, "organization_id", None) and getattr(request, "organization", None):
            obj.organization = request.organization
        super().save_model(request, obj, form, change)


# Custom Admin Site com Dashboard Integrado
class ACRAdminSite(admin.AdminSite):
    site_header = 'ACR Gestão - Administração'
    site_title = 'ACR Gestão'
    index_title = 'Dashboard Administrativo'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard-stats/', self.admin_view(self.dashboard_stats_view), name='dashboard_stats'),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        """Override da página inicial do admin com dashboard integrado e métricas modernas."""
        extra_context = extra_context or {}

        org = getattr(request, 'organization', None)
        if org:
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)

            # Estatísticas gerais e breakdown por entidade
            stats = {
                'total_clients': models.Person.objects.filter(organization=org, status='active').count(),
                'acr_clients': models.Person.objects.filter(organization=org, status='active', entity_affiliation__in=['acr_only', 'both']).count(),
                'proform_clients': models.Person.objects.filter(organization=org, status='active', entity_affiliation__in=['proform_only', 'both']).count(),

                'total_instructors': models.Instructor.objects.filter(organization=org, is_active=True).count(),
                'acr_instructors': models.Instructor.objects.filter(organization=org, is_active=True, entity_affiliation__in=['acr_only', 'both']).count(),
                'proform_instructors': models.Instructor.objects.filter(organization=org, is_active=True, entity_affiliation__in=['proform_only', 'both']).count(),

                'total_modalities': models.Modality.objects.filter(organization=org, is_active=True).count(),
                'acr_modalities': models.Modality.objects.filter(organization=org, is_active=True, entity_type__in=['acr', 'both']).count(),
                'proform_modalities': models.Modality.objects.filter(organization=org, is_active=True, entity_type__in=['proform', 'both']).count(),
            }

            # Receita mensal
            monthly_payments = models.Payment.objects.filter(organization=org, status='completed', paid_date__gte=month_start)
            stats['monthly_revenue'] = sum(p.amount for p in monthly_payments)

            # Próximos eventos (24h)
            upcoming_events = models.Event.objects.filter(
                organization=org,
                starts_at__gte=timezone.now(),
                starts_at__lte=timezone.now() + timedelta(days=1)
            ).select_related('resource', 'modality', 'instructor').annotate(
                bookings_count=Count('bookings', filter=Q(bookings__status='confirmed'))
            ).order_by('starts_at')[:8]
            stats['upcoming_events'] = upcoming_events

            # Clientes recentes (7 dias)
            recent_clients = models.Person.objects.filter(
                organization=org,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).order_by('-created_at')[:6]
            stats['recent_clients'] = recent_clients

            extra_context['stats'] = stats

        return super().index(request, extra_context)

    def dashboard_stats_view(self, request):
        """API endpoint para atualizar estatísticas via AJAX."""
        org = getattr(request, 'organization', None)
        if not org:
            return JsonResponse({'error': 'No organization found'})

        stats = {
            'total_clients': models.Person.objects.filter(organization=org, status='active').count(),
            'total_instructors': models.Instructor.objects.filter(organization=org, is_active=True).count(),
            'total_modalities': models.Modality.objects.filter(organization=org, is_active=True).count(),
            'total_resources': models.Resource.objects.filter(organization=org, is_available=True).count(),
            'total_payment_plans': models.PaymentPlan.objects.filter(organization=org, is_active=True).count(),
            'total_class_groups': models.ClassGroup.objects.filter(organization=org, is_active=True).count(),
        }
        return JsonResponse(stats)

# Criar instância do custom admin site com namespace 'admin'
admin_site = ACRAdminSite(name='admin')


# Definir Admin Classes
@admin.register(models.Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name","domain","org_type")
    search_fields = ("name","domain")
    fieldsets = (
        ("Identificação", {"fields": ("name","domain","org_type")}),
        ("Branding", {"fields": ("primary_color","secondary_color","logo_svg")}),
        ("Configuração", {"fields": ("settings_json","gym_monthly_fee","wellness_monthly_fee")}),
    )


@admin.register(models.Person)
class PersonAdmin(OrgScopedAdmin):
    list_display = ['full_name', 'email', 'phone', 'entity_affiliation', 'status', 'created_at']
    list_filter = ['status', 'entity_affiliation', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'nif']
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'nif', 'photo')
        }),
        ('Detalhes', {
            'fields': ('date_of_birth', 'address', 'emergency_contact', 'entity_affiliation')
        }),
        ('Estado e Notas', {
            'fields': ('status', 'notes'),
            'classes': ('collapse',)
        })
    )


@admin.register(models.Instructor)
class InstructorAdmin(OrgScopedAdmin):
    list_display = ['full_name', 'email', 'phone', 'entity_affiliation', 'is_active'
    ]
    list_filter = ['entity_affiliation', 'is_active', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'photo')
        }),
        ('Especialidades e Afiliação', {
            'fields': ('specialties', 'entity_affiliation')
        }),
        ('Comissões', {
            'fields': ('acr_commission_rate', 'proform_commission_rate'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        })
    )


class ClassGroupAdmin(OrgScopedAdmin):
    """Admin para gestão de turmas."""
    list_display = ['name', 'modality', 'instructor', 'current_members_count', 'max_students', 'level', 'is_active']
    list_filter = ['modality', 'instructor', 'level', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'modality__name', 'instructor__first_name', 'instructor__last_name']
    filter_horizontal = ['members']

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'description', 'modality', 'instructor')
        }),
        ('Configurações', {
            'fields': ('max_students', 'level', 'start_date', 'end_date')
        }),
        ('Membros', {
            'fields': ('members',),
            'description': 'Selecione os clientes que fazem parte desta turma'
        }),
        ('Estado', {
            'fields': ('is_active',)
        })
    )

    def current_members_count(self, obj):
        return obj.current_members_count
    current_members_count.short_description = 'Membros Ativos'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('modality', 'instructor').prefetch_related('members')


class ModalityAdmin(OrgScopedAdmin):
    list_display = ['name', 'entity_type', 'default_duration_minutes', 'max_capacity', 'color_preview', 'is_active']
    list_filter = ['entity_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']

    def color_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 5px 10px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_preview.short_description = 'Cor'


class ResourceAdmin(OrgScopedAdmin):
    list_display = ['name', 'entity_type', 'capacity', 'is_available']
    list_filter = ['entity_type', 'is_available', 'created_at']
    search_fields = ['name', 'description']

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'description', 'entity_type')
        }),
        ('Capacidade e Disponibilidade', {
            'fields': ('capacity', 'is_available')
        }),
        ('Equipamentos e Características', {
            'fields': ('equipment_list', 'special_features'),
            'classes': ('collapse',)
        })
    )


class EventAdmin(OrgScopedAdmin):
    list_display = ['display_title', 'resource', 'instructor', 'event_type', 'starts_at', 'ends_at', 'capacity', 'bookings_count']
    list_filter = ['event_type', 'resource', 'modality', 'instructor', 'starts_at']
    search_fields = ['title', 'description', 'resource__name', 'instructor__first_name', 'instructor__last_name']
    date_hierarchy = 'starts_at'

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('title', 'description', 'event_type')
        }),
        ('Localização e Modalidade', {
            'fields': ('resource', 'modality', 'instructor')
        }),
        ('Participantes', {
            'fields': ('class_group', 'individual_client', 'capacity'),
            'description': 'Configure os participantes baseado no tipo de evento'
        }),
        ('Horário', {
            'fields': ('starts_at', 'ends_at')
        }),
        ('Google Calendar', {
            'fields': ('google_calendar_sync_enabled',),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'resource', 'modality', 'instructor', 'class_group', 'individual_client'
        ).annotate(
            bookings_count_annotated=Count('bookings', filter=Q(bookings__status='confirmed'))
        )


class PaymentPlanAdmin(OrgScopedAdmin):
    list_display = ['name', 'plan_type', 'entity_type', 'price', 'credits_included', 'is_active']
    list_filter = ['plan_type', 'entity_type', 'is_active']
    search_fields = ['name', 'description']
    filter_horizontal = ['modalities']


@admin.register(models.Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "channel", "organization", "scheduled_at", "sent_at")
    list_filter = ("channel", "scheduled_at")
    search_fields = ("name", "content")


@admin.register(models.MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ("campaign", "person", "channel", "status", "created_at")
    list_filter = ("channel", "status", "created_at")
    search_fields = ("person__first_name", "person__last_name", "campaign__name")


# Registar todos os modelos no custom admin site
admin_site.register(models.Organization, OrganizationAdmin)
admin_site.register(models.Person, PersonAdmin)
admin_site.register(models.Instructor, InstructorAdmin)
admin_site.register(models.ClassGroup, ClassGroupAdmin)
admin_site.register(models.Modality, ModalityAdmin)
admin_site.register(models.Resource, ResourceAdmin)
admin_site.register(models.Event, EventAdmin)
admin_site.register(models.PaymentPlan, PaymentPlanAdmin)
admin_site.register(models.ClientSubscription)
admin_site.register(models.Booking)
admin_site.register(models.Payment)
admin_site.register(models.InstructorCommission)
