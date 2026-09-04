"""
Serviço do Quiosque e Controlo de Acesso no Tapete / Pavilhão da ACR.
Valida em tempo real o QR Code, Número de Sócio ou NIF, inspeciona seguro,
atestado médico e quotas associativas, e efetua o check-in na aula em curso.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Dict, Any, Optional

from django.utils import timezone
from django.db.models import Q

from ..models import Organization, Person, Event, Booking


def resolve_person(organization: Organization, identifier: str) -> Optional[Person]:
    """Identifica o sócio/praticante por QR Code, NIF, Número de Sócio ou Telefone."""
    identifier = (identifier or "").strip()
    if not identifier:
        return None

    # Formato do QR Code: ACR:<org_id>:<person_id>:<token>
    if identifier.startswith("ACR:"):
        parts = identifier.split(":")
        if len(parts) == 4:
            try:
                p_id = int(parts[2])
                token = parts[3]
                return Person.objects.filter(
                    organization=organization, id=p_id, qr_code_token=token
                ).first()
            except (ValueError, IndexError):
                pass

    # Pesquisa direta por token de QR Code
    person = Person.objects.filter(organization=organization, qr_code_token=identifier).first()
    if person:
        return person

    # Pesquisa por NIF
    person = Person.objects.filter(organization=organization, nif=identifier).first()
    if person:
        return person

    # Pesquisa por Número de Sócio (ex: "15" ou "#15")
    clean_num = identifier.lstrip("#").strip()
    if clean_num.isdigit():
        person = Person.objects.filter(organization=organization, member_number=int(clean_num)).first()
        if person:
            return person

    # Pesquisa por Telefone
    person = Person.objects.filter(organization=organization, phone=identifier).first()
    if person:
        return person

    return None


def get_active_event_for_facility(organization: Organization, specific_event_id: Optional[int] = None) -> Optional[Event]:
    """Determina a aula que está a decorrer no momento ou nos próximos 30 minutos."""
    now = timezone.now()

    if specific_event_id:
        return Event.objects.filter(organization=organization, id=specific_event_id).first()

    # Janela: começou há no máximo 45 minutos ou vai começar nos próximos 30 minutos
    start_window = now - timedelta(minutes=45)
    end_window = now + timedelta(minutes=30)

    return Event.objects.filter(
        organization=organization,
        starts_at__gte=start_window,
        starts_at__lte=end_window,
    ).select_related('resource', 'modality', 'instructor').order_by('starts_at').first()


def process_kiosk_checkin(
    organization: Organization,
    identifier: str,
    specific_event_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Processa a validação de acesso e check-in no Quiosque.
    Retorna resultado com semáforo de validação (green, yellow, red) e mensagens explicativas.
    """
    person = resolve_person(organization, identifier)
    if not person:
        return {
            "success": False,
            "status": "red",
            "title": "Não Encontrado",
            "message": "Nenhum sócio ou praticante localizado com este código/número.",
            "person": None,
        }

    # 1. Auditoria de Seguros e Atestado Médico
    ins_status = person.insurance_status
    med_status = person.medical_status
    fee_status = person.membership_fee_status

    warnings = []
    blocking_reasons = []

    # Validação do Seguro Obrigatório (Protocolo Generali)
    if not ins_status.get("is_valid", False):
        blocking_reasons.append("Seguro desportivo vencido ou sem apólice ativa.")
    elif ins_status.get("status") == "warning":
        warnings.append(ins_status.get("label", "Seguro a expirar em breve."))

    # Validação do Atestado Médico (IPDJ)
    if not med_status.get("is_valid", False):
        blocking_reasons.append("Atestado / exame médico-desportivo vencido.")
    elif med_status.get("status") == "warning":
        warnings.append(med_status.get("label", "Atestado médico a caducar em breve."))

    # Validação de Quotas da ACR
    if fee_status == "overdue":
        warnings.append("Quotas associativas da ACR pendentes de regularização.")

    # Determinação do Semáforo
    if blocking_reasons:
        traffic_status = "red"
        status_label = "Acesso Condicionado"
    elif warnings:
        traffic_status = "yellow"
        status_label = "Acesso Permitido com Aviso"
    else:
        traffic_status = "green"
        status_label = "Entrada Autorizada"

    # 2. Check-in na Aula Ativa
    active_event = get_active_event_for_facility(organization, specific_event_id)
    checked_in = False
    event_info = None

    if active_event and traffic_status != "red":
        booking, _ = Booking.objects.get_or_create(
            organization=organization,
            event=active_event,
            person=person,
            defaults={"status": Booking.Status.CHECKED_IN}
        )
        if booking.status != Booking.Status.CHECKED_IN:
            booking.status = Booking.Status.CHECKED_IN
            booking.save(update_fields=["status"])

        checked_in = True
        event_info = {
            "id": active_event.id,
            "title": active_event.title,
            "resource_name": active_event.resource.name if active_event.resource else "Instalação",
            "instructor_name": active_event.instructor.full_name if active_event.instructor else "Instrutor",
            "time": f"{active_event.starts_at.strftime('%H:%M')} - {active_event.ends_at.strftime('%H:%M')}",
            "modality": active_event.modality.name if active_event.modality else "Modalidade",
        }

    return {
        "success": True,
        "status": traffic_status,
        "status_label": status_label,
        "person": {
            "id": person.id,
            "full_name": person.full_name,
            "member_number": person.member_number,
            "member_category": person.get_member_category_display(),
            "current_belt": person.current_belt or "Sem graduação atribuída",
            "affiliation": person.get_entity_affiliation_display(),
            "photo_url": person.photo.url if person.photo else None,
        },
        "checked_in": checked_in,
        "event": event_info,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "insurance_policy": ins_status.get("policy", "Sem apólice"),
    }
