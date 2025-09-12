from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import JsonResponse
from django.db.models import Count, Q
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


# Admin Site Simplificado
class ACRAdminSite(admin.AdminSite):
    site_header = 'ACR Gestão - Administração'
    site_title = 'ACR Gestão'
    index_title = 'Dashboard Administrativo'

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}

        org = getattr(request, 'organization', None)
        if org:
            extra_context.update({
                'total_clients': models.Person.objects.filter(organization=org, status='active').count(),
                'total_instructors': models.Instructor.objects.filter(organization=org, is_active=True).count(),
                'total_modalities': models.Modality.objects.filter(organization=org, is_active=True).count(),
                'total_resources': models.Resource.objects.filter(organization=org, is_available=True).count(),
            })

        return super().index(request, extra_context)

# Instância customizada do site de administração
admin_site = ACRAdminSite()


# Admin Classes simplificadas
class PersonAdmin(OrgScopedAdmin):
    list_display = ['full_name', 'email', 'phone', 'entity_affiliation', 'status']
    list_filter = ['status', 'entity_affiliation']
    search_fields = ['first_name', 'last_name', 'email', 'phone']


class InstructorAdmin(OrgScopedAdmin):
    list_display = ['full_name', 'email', 'phone', 'entity_affiliation', 'is_active']
    list_filter = ['entity_affiliation', 'is_active']
    search_fields = ['first_name', 'last_name', 'email', 'phone']


class ModalityAdmin(OrgScopedAdmin):
    list_display = ['name', 'entity_type', 'default_duration_minutes', 'max_capacity', 'is_active']
    list_filter = ['entity_type', 'is_active']
    search_fields = ['name', 'description']


class ResourceAdmin(OrgScopedAdmin):
    list_display = ['name', 'entity_type', 'capacity', 'is_available']
    list_filter = ['entity_type', 'is_available']
    search_fields = ['name', 'description']


class EventAdmin(OrgScopedAdmin):
    list_display = ['display_title', 'resource', 'instructor', 'event_type', 'starts_at', 'ends_at']
    list_filter = ['event_type', 'resource', 'modality', 'instructor']
    search_fields = ['title', 'description']


class PaymentPlanAdmin(OrgScopedAdmin):
    list_display = ['name', 'plan_type', 'entity_type', 'price', 'credits_included', 'is_active']
    list_filter = ['plan_type', 'entity_type', 'is_active']
    search_fields = ['name', 'description']


class ClientSubscriptionAdmin(OrgScopedAdmin):
    list_display = ['person', 'payment_plan', 'status', 'remaining_credits', 'start_date', 'end_date']
    list_filter = ['status', 'payment_plan__plan_type', 'is_paid']
    search_fields = ['person__first_name', 'person__last_name']
    autocomplete_fields = ['person', 'payment_plan']


class BookingAdmin(OrgScopedAdmin):
    list_display = ['person', 'event', 'status', 'credits_used', 'is_paid', 'created_at']
    list_filter = ['status', 'is_paid']
    search_fields = ['person__first_name', 'person__last_name']
    autocomplete_fields = ['person', 'event']


class PaymentAdmin(OrgScopedAdmin):
    list_display = ['person', 'amount', 'method', 'status', 'due_date', 'paid_date']
    list_filter = ['method', 'status', 'due_date']
    search_fields = ['person__first_name', 'person__last_name']
    autocomplete_fields = ['person']


class InvoiceItemInline(admin.TabularInline):
    model = models.InvoiceItem
    extra = 1
    fields = ['description', 'quantity', 'unit_price']


class InvoiceAdmin(OrgScopedAdmin):
    list_display = ['person', 'issue_date', 'total', 'status']
    search_fields = ['person__first_name', 'person__last_name', 'person__email']
    inlines = [InvoiceItemInline]


class PriceInline(admin.TabularInline):
    model = models.Price
    extra = 1
    fields = ['amount', 'currency', 'valid_from', 'valid_to']

class ProductAdmin(OrgScopedAdmin):
    readonly_fields = ['price']
    inlines = [PriceInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, models.Price) and not obj.organization_id:
                obj.organization = form.instance.organization
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

# Registar modelos no site de administração
admin_site.register(models.Person, PersonAdmin)
admin_site.register(models.Instructor, InstructorAdmin)
admin_site.register(models.Modality, ModalityAdmin)
admin_site.register(models.Resource, ResourceAdmin)
admin_site.register(models.Event, EventAdmin)
admin_site.register(models.PaymentPlan, PaymentPlanAdmin)
admin_site.register(models.ClientSubscription, ClientSubscriptionAdmin)
admin_site.register(models.Booking, BookingAdmin)
admin_site.register(models.Payment, PaymentAdmin)

# Modelos simples
admin_site.register(models.Organization)
admin_site.register(models.ClassGroup)
admin_site.register(models.InstructorCommission)
admin_site.register(models.CreditHistory)
admin_site.register(models.UserProfile)
admin_site.register(models.Product, ProductAdmin)
admin_site.register(models.Membership)
admin_site.register(models.ClassTemplate)
admin_site.register(models.GoogleCalendarConfig)
admin_site.register(models.InstructorGoogleCalendar)
admin_site.register(models.GoogleCalendarSyncLog)
admin_site.register(models.SystemAlert)
admin_site.register(models.Invoice, InvoiceAdmin)
admin_site.register(models.Campaign)
admin_site.register(models.MessageLog)
