from django.contrib import admin
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
    list_display = ("name", "domain")
    search_fields = ("name", "domain")


@admin.register(models.Person)
class PersonAdmin(OrgScopedAdmin):
    list_display = ("first_name", "last_name", "email", "nif", "organization")
    search_fields = ("first_name", "last_name", "email", "nif")


@admin.register(models.Membership)
class MembershipAdmin(OrgScopedAdmin):
    list_display = ("person", "plan", "status", "starts_on", "ends_on")
    list_filter = ("status",)


@admin.register(models.Product)
class ProductAdmin(OrgScopedAdmin):
    list_display = ("name", "kind", "organization")
    list_filter = ("kind",)


@admin.register(models.Price)
class PriceAdmin(OrgScopedAdmin):
    list_display = ("product", "amount", "currency", "valid_from", "valid_to")


@admin.register(models.Resource)
class ResourceAdmin(OrgScopedAdmin):
    list_display = ("name", "capacity")


@admin.register(models.ClassTemplate)
class ClassTemplateAdmin(OrgScopedAdmin):
    list_display = ("title", "default_capacity", "default_duration_minutes")


@admin.register(models.Event)
class EventAdmin(OrgScopedAdmin):
    list_display = ("title", "resource", "starts_at", "ends_at", "capacity")
    list_filter = ("resource", "starts_at")


@admin.register(models.Booking)
class BookingAdmin(OrgScopedAdmin):
    list_display = ("event", "person", "status", "created_at")
    list_filter = ("status",)


class InvoiceItemInline(admin.TabularInline):
    model = models.InvoiceItem
    extra = 1


@admin.register(models.Invoice)
class InvoiceAdmin(OrgScopedAdmin):
    list_display = ("id", "person", "issue_date", "total", "status")
    inlines = [InvoiceItemInline]
    list_filter = ("status",)
