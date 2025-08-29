from django.contrib import admin, messages
from django.db.models import Q

from .models import (
    Organization, Person, OrgMembership, Guardian, Athlete, GymClient, Instructor,
    Modality, Enrollment, Account, Product, Price, DiscountRule,
)


# ---------------------------
# Mixin: filtra e preenche organization automaticamente
# ---------------------------
class ScopedByOrgAdmin(admin.ModelAdmin):
    """Filtra por request.organization nos modelos com FK 'organization' e
    preenche automaticamente ao gravar (se ainda não estiver definido)."""

    org_fk_name = "organization"

    def _model_has_org(self, model):
        return any(f.name == self.org_fk_name for f in model._meta.fields)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        org = getattr(request, "organization", None)
        if org and self._model_has_org(qs.model):
            return qs.filter(**{self.org_fk_name: org})
        return qs

    def save_model(self, request, obj, form, change):
        org = getattr(request, "organization", None)
        if org and self._model_has_org(type(obj)) and getattr(obj, f"{self.org_fk_name}_id", None) is None:
            setattr(obj, self.org_fk_name, org)
        super().save_model(request, obj, form, change)


# ---------------------------
# Organization
# ---------------------------
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "domain")
    search_fields = ("name", "domain")
    ordering = ("name",)


# ---------------------------
# Person & OrgMembership
# ---------------------------
@admin.register(OrgMembership)
class OrgMembershipAdmin(ScopedByOrgAdmin):
    list_display = ("person", "organization", "roles", "numero_socio")
    search_fields = ("person__nome", "numero_socio")
    list_filter = ("organization",)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "telefone", "membro_de")
    search_fields = ("nome", "email", "telefone", "nif")
    actions = ("add_membership_current_org", "create_account_current_org")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        org = getattr(request, "organization", None)
        if org:
            # Mostra só pessoas que tenham membership nesta organização
            return qs.filter(memberships__organization=org).distinct()
        return qs

    def membro_de(self, obj):
        orgs = obj.memberships.values_list("organization__name", flat=True)
        return ", ".join(sorted(set(orgs))) or "—"
    membro_de.short_description = "Membro de"

    @admin.action(description="Adicionar membership na organização atual")
    def add_membership_current_org(self, request, queryset):
        org = getattr(request, "organization", None)
        if not org:
            messages.error(request, "Sem organização no contexto (domínio).")
            return
        created = 0
        for person in queryset:
            obj, was_created = OrgMembership.objects.get_or_create(
                person=person,
                organization=org,
                defaults={"roles": []},
            )
            if was_created:
                created += 1
        messages.success(request, f"Memberships criados: {created}")

    @admin.action(description="Criar conta financeira na organização atual")
    def create_account_current_org(self, request, queryset):
        org = getattr(request, "organization", None)
        if not org:
            messages.error(request, "Sem organização no contexto (domínio).")
            return
        from .models import Account
        created = 0
        for person in queryset:
            obj, was_created = Account.objects.get_or_create(
                person=person,
                organization=org,
            )
            if was_created:
                created += 1
        messages.success(request, f"Contas financeiras criadas: {created}")


# ---------------------------
# Perfis & contactos
# ---------------------------
@admin.register(Guardian)
class GuardianAdmin(ScopedByOrgAdmin):
    list_display = ("nome", "relacao", "telefone", "email", "organization")
    search_fields = ("nome", "email", "telefone")
    list_filter = ("organization",)


@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    list_display = ("person", "is_active", "guardian")
    list_filter = ("is_active",)
    search_fields = ("person__nome", "guardian__nome")


@admin.register(GymClient)
class GymClientAdmin(admin.ModelAdmin):
    list_display = ("person", "numero_socio")
    search_fields = ("person__nome", "numero_socio")


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ("person", "ativo")
    list_filter = ("ativo",)
    search_fields = ("person__nome", "user__username")


# ---------------------------
# Modalidades & Inscrições
# ---------------------------
@admin.register(Modality)
class ModalityAdmin(ScopedByOrgAdmin):
    list_display = ("nome", "organization")
    search_fields = ("nome",)
    list_filter = ("organization",)


@admin.register(Enrollment)
class EnrollmentAdmin(ScopedByOrgAdmin):
    list_display = ("person", "modality", "epoca", "estado", "organization")
    list_filter = ("estado", "epoca", "organization", "modality")
    search_fields = ("person__nome", "modality__nome")


# ---------------------------
# Faturação
# ---------------------------
class PriceInline(admin.TabularInline):
    model = Price
    extra = 0
    ordering = ("-active_from",)


@admin.register(Product)
class ProductAdmin(ScopedByOrgAdmin):
    list_display = ("name", "kind", "organization")
    list_filter = ("kind", "organization")
    search_fields = ("name",)
    inlines = [PriceInline]


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ("product", "active_from", "amount")
    list_filter = ("active_from", "product__organization", "product__kind")
    search_fields = ("product__name",)


@admin.register(Account)
class AccountAdmin(ScopedByOrgAdmin):
    list_display = ("person", "organization")
    list_filter = ("organization",)
    search_fields = ("person__nome",)


@admin.register(DiscountRule)
class DiscountRuleAdmin(ScopedByOrgAdmin):
    list_display = ("name", "organization", "requires_dual_org", "percent")
    list_filter = ("organization", "requires_dual_org")
    search_fields = ("name",)
