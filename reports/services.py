from django.db.models import Sum

from core.models import Organization, Person, Event, Payment


def get_summary_data(organization: Organization) -> dict:
    total_payments = (
        Payment.objects.filter(organization=organization, status=Payment.Status.COMPLETED)
        .aggregate(total=Sum('amount'))['total']
        or 0
    )
    return {
        'clients': Person.objects.filter(organization=organization).count(),
        'events': Event.objects.filter(organization=organization).count(),
        'payments_total': float(total_payments),
    }
