from django.contrib import admin
from django.utils.html import format_html
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.urls import path
from django.http import JsonResponse
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
        """Override da página inicial do admin com dashboard integrado."""
        extra_context = extra_context or {}

        org = getattr(request, 'organization', None)
        if org:
            # Estatísticas básicas
            stats = {
                'total_clients': models.Person.objects.filter(organization=org, status='active').count(),
                'total_instructors': models.Instructor.objects.filter(organization=org, is_active=True).count(),
                'total_modalities': models.Modality.objects.filter(organization=org, is_active=True).count(),
            }
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
        }
        return JsonResponse(stats)

# Criar instância do custom admin site
admin_site = ACRAdminSite(name='acr_admin')


@admin.register(models.Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "org_type", "gym_monthly_fee", "wellness_monthly_fee")
    list_filter = ("org_type",)
    search_fields = ("name", "domain")


@admin.register(models.Person)
class PersonAdmin(OrgScopedAdmin):
    list_display = ['full_name', 'email', 'phone', 'status', 'created_at']
    list_filter = ['organization', 'status', 'entity_affiliation', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'nif']


@admin.register(models.Instructor)
class InstructorAdmin(OrgScopedAdmin):
    list_display = ['full_name', 'email', 'phone', 'is_active']
    list_filter = ['organization', 'entity_affiliation', 'is_active', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone']


@admin.register(models.Modality)
class ModalityAdmin(OrgScopedAdmin):
    list_display = ['name', 'entity_type', 'price_per_class', 'is_active']
    list_filter = ['organization', 'entity_type', 'is_active']
    search_fields = ['name', 'description']


@admin.register(models.Payment)
class PaymentAdmin(OrgScopedAdmin):
    list_display = ['person', 'amount', 'method', 'status', 'due_date']
    list_filter = ['organization', 'method', 'status']
    search_fields = ['person__first_name', 'person__last_name']


@admin.register(models.Membership)
class MembershipAdmin(OrgScopedAdmin):
    list_display = ("person", "plan", "status", "starts_on", "ends_on")
    list_filter = ("status", "starts_on")


@admin.register(models.Product)
class ProductAdmin(OrgScopedAdmin):
    list_display = ("name", "kind", "price", "duration_months")
    list_filter = ("kind", "created_at")


@admin.register(models.Resource)
class ResourceAdmin(OrgScopedAdmin):
    list_display = ("name", "capacity")


@admin.register(models.Event)
class EventAdmin(OrgScopedAdmin):
    list_display = ['title', 'resource', 'starts_at', 'ends_at', 'capacity']
    list_filter = ['organization', 'resource', 'starts_at']


@admin.register(models.Booking)
class BookingAdmin(OrgScopedAdmin):
    list_display = ("event", "person", "status", "created_at")
    list_filter = ["status", "created_at"]

# Registrar todos os modelos no custom admin site
admin_site.register(models.Organization, OrganizationAdmin)
admin_site.register(models.Person, PersonAdmin)
admin_site.register(models.Instructor, InstructorAdmin)
admin_site.register(models.Modality, ModalityAdmin)
admin_site.register(models.Payment, PaymentAdmin)
admin_site.register(models.Membership, MembershipAdmin)
admin_site.register(models.Product, ProductAdmin)
admin_site.register(models.Resource, ResourceAdmin)
admin_site.register(models.Event, EventAdmin)
admin_site.register(models.Booking, BookingAdmin)
