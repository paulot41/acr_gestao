from django.core.cache import cache
from django.db.models import Sum

from core.models import Organization, Person, Event, Payment


def get_summary_data(organization: Organization) -> dict:
    cache_key = f"reports:summary:{organization.id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    total_payments = (
        Payment.objects.filter(organization=organization, status=Payment.Status.COMPLETED)
        .aggregate(total=Sum('amount'))['total']
        or 0
    )
    payload = {
        'clients': Person.objects.filter(organization=organization).count(),
        'events': Event.objects.filter(organization=organization).count(),
        'payments_total': float(total_payments),
    }
    cache.set(cache_key, payload, timeout=60)
    return payload
