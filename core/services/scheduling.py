from __future__ import annotations
from django.db.models import Q
from django.core.exceptions import ValidationError
from core.models import Event, Booking


def ensure_no_conflict(event: Event) -> None:
    qs = Event.objects.filter(
        organization=event.organization,
        resource=event.resource
    ).exclude(pk=event.pk)
    overlap = qs.filter(
        Q(starts_at__lt=event.ends_at) & Q(ends_at__gt=event.starts_at)
    ).exists()
    if overlap:
        raise ValidationError("Conflito: já existe um evento neste recurso no mesmo intervalo.")


def ensure_capacity(booking: Booking) -> None:
    event = booking.event
    if event.is_full and booking.status != Booking.Status.CANCELLED:
        raise ValidationError("Lotação esgotada para este evento.")
