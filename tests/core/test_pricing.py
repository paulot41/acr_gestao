from datetime import date

import pytest

from core.models import Organization, Person, Product, Price
from core.services.pricing import compute_price


@pytest.mark.django_db
def test_compute_price_uses_active_price():
    org = Organization.objects.create(name="Org", domain="org.test")
    person = Person.objects.create(
        organization=org,
        first_name="Ana",
        email="ana@example.com",
        nif="123456789",
    )
    product = Product.objects.create(
        organization=org,
        name="Plano",
        description="",
        price=10,
        duration_months=1,
    )
    Price.objects.create(
        organization=org,
        product=product,
        amount=25,
        valid_from=date.today(),
    )

    amount = compute_price(person, product, date.today())
    assert amount == 25


@pytest.mark.django_db
def test_compute_price_without_price_raises():
    org = Organization.objects.create(name="Org2", domain="org2.test")
    person = Person.objects.create(
        organization=org,
        first_name="Bea",
        email="bea@example.com",
        nif="987654321",
    )
    product = Product.objects.create(
        organization=org,
        name="Plano",
        description="",
        price=10,
        duration_months=1,
    )

    with pytest.raises(ValueError):
        compute_price(person, product, date.today())
