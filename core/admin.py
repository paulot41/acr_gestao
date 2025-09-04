from django.contrib import admin
from django.utils.html import format_html
from . import models


class OrgScopedAdmin(admin.ModelAdmin):
    list_filter = ["organization"]

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


@admin.register(models.Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "org_type", "gym_monthly_fee", "wellness_monthly_fee")
    list_filter = ("org_type",)
    search_fields = ("name", "domain")
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'domain', 'org_type')
        }),
        ('Configurações Financeiras', {
            'fields': ('gym_monthly_fee', 'wellness_monthly_fee')
        }),
        ('Configurações Avançadas', {
            'fields': ('settings_json',),
            'classes': ('collapse',)
        }),
    )


@admin.register(models.Person)
class PersonAdmin(OrgScopedAdmin):
    list_display = ['full_name', 'entity_affiliation_badge', 'email', 'phone', 'status', 'monthly_fee', 'created_at']
    list_filter = ['organization', 'status', 'entity_affiliation', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'nif']
    readonly_fields = ['created_at', 'monthly_fee']

    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'nif', 'date_of_birth', 'photo')
        }),
        ('Entidade e Status', {
            'fields': ('entity_affiliation', 'status')
        }),
        ('Contactos', {
            'fields': ('address', 'emergency_contact')
        }),
        ('Informações do Sistema', {
            'fields': ('created_at', 'last_activity', 'notes'),
            'classes': ('collapse',)
        }),
    )

    def entity_affiliation_badge(self, obj):
        colors = {
            'acr_only': '#0d6efd',
            'proform_only': '#198754',
            'both': 'linear-gradient(90deg, #0d6efd 50%, #198754 50%)'
        }
        labels = {
            'acr_only': 'ACR',
            'proform_only': 'Proform',
            'both': 'ACR + Proform'
        }
        color = colors.get(obj.entity_affiliation, '#6c757d')
        label = labels.get(obj.entity_affiliation, obj.get_entity_affiliation_display())

        if obj.entity_affiliation == 'both':
            return format_html(
                '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
                color, label
            )
        else:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
                color, label
            )
    entity_affiliation_badge.short_description = 'Entidade'

    def monthly_fee(self, obj):
        return f"€{obj.get_monthly_fee():.0f}"
    monthly_fee.short_description = 'Mensalidade'


@admin.register(models.Instructor)
class InstructorAdmin(OrgScopedAdmin):
    list_display = ['full_name', 'entity_affiliation_badge', 'email', 'phone', 'acr_commission_rate', 'proform_commission_rate', 'is_active']
    list_filter = ['organization', 'entity_affiliation', 'is_active', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'specialties']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'photo', 'specialties')
        }),
        ('Entidade e Comissões', {
            'fields': ('entity_affiliation', 'acr_commission_rate', 'proform_commission_rate')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )

    def entity_affiliation_badge(self, obj):
        colors = {
            'acr_only': '#0d6efd',
            'proform_only': '#198754',
            'both': 'linear-gradient(90deg, #0d6efd 50%, #198754 50%)'
        }
        labels = {
            'acr_only': 'ACR',
            'proform_only': 'Proform',
            'both': 'ACR + Proform'
        }
        color = colors.get(obj.entity_affiliation, '#6c757d')
        label = labels.get(obj.entity_affiliation, obj.get_entity_affiliation_display())

        if obj.entity_affiliation == 'both':
            return format_html(
                '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
                color, label
            )
        else:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
                color, label
            )
    entity_affiliation_badge.short_description = 'Entidade'


@admin.register(models.Modality)
class ModalityAdmin(OrgScopedAdmin):
    list_display = ['name', 'entity_type_badge', 'price_per_class', 'default_duration_minutes', 'max_capacity', 'color_preview', 'is_active']
    list_filter = ['organization', 'entity_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'description', 'entity_type')
        }),
        ('Configurações', {
            'fields': ('default_duration_minutes', 'max_capacity', 'price_per_class')
        }),
        ('Aparência', {
            'fields': ('color', 'is_active')
        }),
        ('Sistema', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def entity_type_badge(self, obj):
        colors = {
            'acr': '#0d6efd',
            'proform': '#198754',
            'both': 'linear-gradient(90deg, #0d6efd 50%, #198754 50%)'
        }
        labels = {
            'acr': 'ACR',
            'proform': 'Proform',
            'both': 'Ambas'
        }
        color = colors.get(obj.entity_type, '#6c757d')
        label = labels.get(obj.entity_type, obj.get_entity_type_display())

        if obj.entity_type == 'both':
            return format_html(
                '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
                color, label
            )
        else:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
                color, label
            )
    entity_type_badge.short_description = 'Entidade'

    def color_preview(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 4px; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_preview.short_description = 'Cor'


@admin.register(models.Payment)
class PaymentAdmin(OrgScopedAdmin):
    list_display = ['person', 'amount', 'method', 'status', 'due_date', 'paid_date', 'is_overdue_display']
    list_filter = ['organization', 'method', 'status', 'due_date', 'paid_date', 'created_at']
    search_fields = ['person__first_name', 'person__last_name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'is_overdue_display']
    date_hierarchy = 'due_date'

    fieldsets = (
        ('Informações do Pagamento', {
            'fields': ('person', 'amount', 'description')
        }),
        ('Método e Status', {
            'fields': ('method', 'status')
        }),
        ('Datas', {
            'fields': ('due_date', 'paid_date')
        }),
        ('Notas e Sistema', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def is_overdue_display(self, obj):
        if obj.is_overdue():
            return format_html('<span style="color: red; font-weight: bold;">Em Atraso</span>')
        return format_html('<span style="color: green;">OK</span>')
    is_overdue_display.short_description = 'Estado'


@admin.register(models.InstructorCommission)
class InstructorCommissionAdmin(OrgScopedAdmin):
    list_display = ['instructor', 'event', 'total_revenue', 'instructor_amount', 'entity_amount', 'commission_rate', 'is_paid']
    list_filter = ['organization', 'is_paid', 'payment_date', 'created_at']
    search_fields = ['instructor__first_name', 'instructor__last_name', 'event__title']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('instructor', 'event')
        }),
        ('Valores Financeiros', {
            'fields': ('total_revenue', 'commission_rate', 'instructor_amount', 'entity_amount')
        }),
        ('Pagamento', {
            'fields': ('is_paid', 'payment_date')
        }),
        ('Notas', {
            'fields': ('notes', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(models.Membership)
class MembershipAdmin(OrgScopedAdmin):
    list_display = ("person", "plan", "status", "starts_on", "ends_on")
    list_filter = ("status", "starts_on")
    search_fields = ['person__first_name', 'person__last_name', 'plan']
    date_hierarchy = 'starts_on'


@admin.register(models.Product)
class ProductAdmin(OrgScopedAdmin):
    list_display = ("name", "kind", "price", "duration_months", "organization")
    list_filter = ("kind", "created_at")
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(models.Price)
class PriceAdmin(OrgScopedAdmin):
    list_display = ("product", "amount", "currency", "valid_from", "valid_to", "is_active_display")
    list_filter = ("currency", "valid_from")
    readonly_fields = ['is_active_display']

    def is_active_display(self, obj):
        from django.utils import timezone
        if obj.is_active_on(timezone.now().date()):
            return format_html('<span style="color: green; font-weight: bold;">Ativo</span>')
        return format_html('<span style="color: red;">Inativo</span>')
    is_active_display.short_description = 'Estado'


@admin.register(models.Resource)
class ResourceAdmin(OrgScopedAdmin):
    list_display = ("name", "capacity")
    search_fields = ['name']


@admin.register(models.ClassTemplate)
class ClassTemplateAdmin(OrgScopedAdmin):
    list_display = ("title", "default_capacity", "default_duration_minutes")
    search_fields = ['title']


@admin.register(models.Event)
class EventAdmin(OrgScopedAdmin):
    list_display = ['title', 'resource', 'starts_at', 'ends_at', 'capacity', 'bookings_count', 'is_full_display']
    list_filter = ['organization', 'resource', 'starts_at']
    search_fields = ['title']
    readonly_fields = ['bookings_count', 'is_full_display']
    date_hierarchy = 'starts_at'

    def bookings_count(self, obj):
        return obj.bookings_count
    bookings_count.short_description = 'Reservas'

    def is_full_display(self, obj):
        if obj.is_full:
            return format_html('<span style="color: red; font-weight: bold;">Lotado</span>')
        return format_html('<span style="color: green;">Disponível</span>')
    is_full_display.short_description = 'Estado'


@admin.register(models.Booking)
class BookingAdmin(OrgScopedAdmin):
    list_display = ("event", "person", "status", "created_at")
    list_filter = ["status", "created_at", "event__resource"]
    search_fields = ['person__first_name', 'person__last_name', 'event__title']
    date_hierarchy = 'created_at'


@admin.register(models.Invoice)
class InvoiceAdmin(OrgScopedAdmin):
    list_display = ("person", "issue_date", "total", "status")
    list_filter = ["status", "issue_date"]
    search_fields = ['person__first_name', 'person__last_name']
    readonly_fields = ['total']
    date_hierarchy = 'issue_date'


@admin.register(models.InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "description", "quantity", "unit_price", "total")
    search_fields = ['description']

    def total(self, obj):
        return obj.quantity * obj.unit_price
    total.short_description = 'Total'
