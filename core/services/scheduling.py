"""
Serviços de validação de agendamento e capacidade para Eventos e Reservas.
Estes utilitários são usados pelos modelos (Event.clean e Booking.clean).
"""
from __future__ import annotations

from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

# Import lazy to avoid circulars in import time; used only at runtime
from .. import models as app_models


def ensure_no_conflict(event: "app_models.Event") -> None:
    """Garante que não existe conflito horário para o mesmo recurso.

    Regras:
    - Um evento não pode sobrepor outro no mesmo recurso dentro da mesma organização.
    - Ignora o próprio evento em edições.
    """
    if not event.organization_id or not event.resource_id or not event.starts_at or not event.ends_at:
        return  # Campos incompletos; validações de presença ocorrem noutro sítio

    qs = app_models.Event.objects.filter(
        organization=event.organization,
        resource=event.resource,
        starts_at__lt=event.ends_at,
        ends_at__gt=event.starts_at,
    )
    if event.pk:
        qs = qs.exclude(pk=event.pk)

    if qs.exists():
        raise ValidationError("Conflito de horário: já existe um evento no mesmo espaço e intervalo.")


def ensure_capacity(booking: "app_models.Booking") -> None:
    """Valida capacidade do evento e regras básicas da reserva.

    Regras:
    - Evento deve ter capacidade > reservas confirmadas (exclui canceladas).
    - Para eventos individuais, só 1 participante.
    - Para eventos de turma, capacidade segue a do evento.
    """
    event = booking.event
    if not event or not booking.organization_id:
        return

    # Contar reservas confirmadas existentes (excluindo a própria em update)
    confirmed_qs = app_models.Booking.objects.filter(
        organization=booking.organization,
        event=event,
        status=app_models.Booking.Status.CONFIRMED,
    )
    if booking.pk:
        confirmed_qs = confirmed_qs.exclude(pk=booking.pk)

    confirmed_count = confirmed_qs.count()

    # Capacidade efetiva
    capacity = event.capacity or 0
    if capacity <= confirmed_count:
        raise ValidationError("Evento sem vagas disponíveis.")

    # Extra: para eventos individuais reforçar regra de 1 lugar
    if event.event_type == app_models.Event.EventType.INDIVIDUAL and confirmed_count >= 1:
        raise ValidationError("Aula individual já tem um participante.")


