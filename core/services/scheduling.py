from __future__ import annotations

"""
Serviços de validação de agendamento e capacidade para Eventos e Reservas.
Estes utilitários são usados pelos modelos (Event.clean e Booking.clean).
"""
import uuid
from datetime import date, datetime, timedelta, time
from django.utils import timezone
from django.core.exceptions import ValidationError

# Import lazy to avoid circulars in import time; used only at runtime
from .. import models as app_models


def ensure_no_conflict(event: "app_models.Event") -> None:
    """Garante que não existe conflito horário para o mesmo recurso.

    Regras:
    - Um evento não pode sobrepor outro no mesmo recurso dentro da mesma organização.
    - O mesmo instrutor não pode ter aulas sobrepostas (mesmo em salas distintas) dentro da mesma organização.
    - Ignora o próprio evento em edições.
    """
    if not event.organization_id or not event.starts_at or not event.ends_at:
        return  # Campos incompletos; validações de presença ocorrem noutro sítio

    # 1. Validação de conflito de espaço/recurso
    if event.resource_id:
        qs = app_models.Event.objects.filter(
            organization_id=event.organization_id,
            resource_id=event.resource_id,
            starts_at__lt=event.ends_at,
            ends_at__gt=event.starts_at,
        )
        if event.pk:
            qs = qs.exclude(pk=event.pk)

        if qs.exists():
            raise ValidationError("Conflito de horário: já existe um evento no mesmo espaço e intervalo.")

    # 2. Validação de conflito de instrutor
    if event.instructor_id:
        inst_qs = app_models.Event.objects.filter(
            organization_id=event.organization_id,
            instructor_id=event.instructor_id,
            starts_at__lt=event.ends_at,
            ends_at__gt=event.starts_at,
        )
        if event.pk:
            inst_qs = inst_qs.exclude(pk=event.pk)

        if inst_qs.exists():
            raise ValidationError("Conflito de instrutor: o instrutor já tem uma aula agendada neste horário.")


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


def create_recurring_event_series(
    *,
    organization: app_models.Organization,
    resource: app_models.Resource,
    start_time: str | time,
    end_time: str | time,
    start_date: str | date,
    end_date: str | date,
    weekdays: list[int],
    title: str,
    event_type: str = "open_class",
    capacity: int | None = None,
    description: str = "",
    modality: app_models.Modality | None = None,
    instructor: app_models.Instructor | None = None,
    class_group: app_models.ClassGroup | None = None,
    individual_client: app_models.Person | None = None,
) -> dict:
    """Cria uma série de eventos recorrentes com prevenção atómica de conflitos por ocorrência.

    Parâmetros:
    - organization: Organização titular
    - resource: Instalação/Sala
    - start_time: Hora de início ('HH:MM' ou time)
    - end_time: Hora de fim ('HH:MM' ou time)
    - start_date: Data de início ('YYYY-MM-DD' ou date)
    - end_date: Data de fim ('YYYY-MM-DD' ou date)
    - weekdays: Lista de dias da semana (0=Segunda, 1=Terça, ..., 6=Domingo)
    - title: Título dos eventos
    - event_type: Tipo de evento (open_class, group_class, individual)
    - capacity: Capacidade máxima (se None, herda do recurso ou turma)
    - description: Descrição do evento
    - modality: Modalidade desportiva
    - instructor: Instrutor responsável
    - class_group: Turma associada
    - individual_client: Atleta para aula individual
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    if start_date > end_date:
        raise ValidationError("A data de término deve ser posterior ou igual à data de início.")

    if (end_date - start_date).days > 366:
        raise ValidationError("A série recorrente não pode exceder 366 dias (1 ano).")

    if not weekdays:
        raise ValidationError("Deve selecionar pelo menos um dia da semana para a recorrência.")

    # Processar horas
    if isinstance(start_time, str):
        sh, sm = map(int, start_time.split(":")[:2])
        parsed_start_time = time(sh, sm)
    else:
        parsed_start_time = start_time

    if isinstance(end_time, str):
        eh, em = map(int, end_time.split(":")[:2])
        parsed_end_time = time(eh, em)
    else:
        parsed_end_time = end_time

    if parsed_end_time <= parsed_start_time:
        raise ValidationError("A hora de fim deve ser posterior à hora de início.")

    series_id = uuid.uuid4()
    created_events = []
    skipped_dates = []

    current = start_date
    while current <= end_date:
        if current.weekday() in weekdays:
            s_dt = timezone.make_aware(datetime.combine(current, parsed_start_time))
            e_dt = timezone.make_aware(datetime.combine(current, parsed_end_time))

            event = app_models.Event(
                organization=organization,
                resource=resource,
                modality=modality,
                instructor=instructor,
                title=title,
                description=description,
                starts_at=s_dt,
                ends_at=e_dt,
                event_type=event_type,
                capacity=capacity or (resource.capacity if resource else 0),
                class_group=class_group,
                individual_client=individual_client,
                recurrence_group_id=series_id,
            )

            try:
                event.clean()
                event.save()
                created_events.append(event)
            except ValidationError as err:
                msg = err.messages[0] if hasattr(err, "messages") and err.messages else str(err)
                skipped_dates.append({
                    "date": current.isoformat(),
                    "weekday": current.weekday(),
                    "reason": msg,
                })

        current += timedelta(days=1)

    return {
        "recurrence_group_id": str(series_id),
        "created_count": len(created_events),
        "created_ids": [e.id for e in created_events],
        "skipped_count": len(skipped_dates),
        "skipped_dates": skipped_dates,
    }



