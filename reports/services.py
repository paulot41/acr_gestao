from django.db.models import Sum

from core.models import Person, Event, Payment


def get_summary_data() -> dict:
    total_payments = (
        Payment.objects.filter(status=Payment.Status.COMPLETED)
        .aggregate(total=Sum('amount'))['total']
        or 0
    )
    return {
        'clients': Person.objects.count(),
        'events': Event.objects.count(),
        'payments_total': float(total_payments),
    }
