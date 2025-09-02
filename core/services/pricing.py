from __future__ import annotations
from datetime import date
from decimal import Decimal
from core.models import Organization, Person, Product, Price, Membership


def has_active_membership(person: Person, org: Organization, day: date) -> bool:
    qs = Membership.objects.filter(person=person, organization=org, status=Membership.Status.ACTIVE)
    return qs.filter(starts_on__lte=day).filter(models.Q(ends_on__isnull=True) | models.Q(ends_on__gte=day)).exists()


def compute_price(person: Person, product: Product, day: date) -> Decimal:
    # Preço ativo para o produto/organização
    price = (
        Price.objects.filter(product=product, organization=product.organization, valid_from__lte=day)
        .filter(models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=day))
        .order_by("-valid_from")
        .first()
    )
    if not price:
        raise ValueError("Sem preço ativo para este produto")

    amount = Decimal(price.amount)

    # Desconto “ACR + Ginásio” (exemplo 10%) — se ambas memberships ativas
    try:
        acr = Organization.objects.get(domain__icontains="acr")
        gym = Organization.objects.get(domain__icontains="gym")
    except Organization.DoesNotExist:
        return amount

    if has_active_membership(person, acr, day) and has_active_membership(person, gym, day):
        amount = (amount * Decimal("0.90")).quantize(Decimal("0.01"))

    return amount
