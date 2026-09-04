"""
Serviço do Cartão Digital de Sócio & Praticante da ACR.
Gera os metadados oficiais do cartão (número de sócio, apólice Generali,
graduação de artes marciais e QR Code seguro para acesso ao pavilhão).
"""
from __future__ import annotations

from typing import Dict, Any
from django.utils import timezone
from ..models import Person, AthleteGraduation, ProtocolConfiguration


def get_membership_card_data(person: Person) -> Dict[str, Any]:
    """Retorna os dados oficiais formatados para o Cartão de Sócio e Praticante da ACR."""
    org = person.organization
    token = person.ensure_qr_token()
    qr_payload = f"ACR:{org.id}:{person.id}:{token}"

    config = org.get_protocol_config()
    insurance_policy = person.insurance_policy or config.insurance_policy_number

    # Modalidades onde tem graduação ou reservas
    graduations = person.graduations.select_related('modality', 'examiner').order_by('-awarded_date')
    recent_belt = graduations.first().rank_name if graduations.exists() else (person.current_belt or "Praticante")

    return {
        "person": person,
        "organization": org,
        "full_name": person.full_name,
        "member_number": person.member_number or "—",
        "member_category": person.get_member_category_display(),
        "membership_fee_status": person.get_membership_fee_status_display(),
        "is_fee_regular": person.membership_fee_status == "up_to_date",
        "admission_date": person.admission_date or person.created_at.date(),
        "nif": person.nif or "—",
        "birth_date": person.date_of_birth,
        "photo_url": person.photo.url if person.photo else None,
        "current_belt": recent_belt,
        "insurance_policy": insurance_policy,
        "insurance_company": config.insurance_company,
        "insurance_expiry": person.insurance_expiry,
        "insurance_status": person.insurance_status,
        "medical_status": person.medical_status,
        "emergency_contact": person.emergency_contact or "—",
        "emergency_relationship": person.emergency_relationship or "",
        "qr_payload": qr_payload,
        "graduations": graduations,
        "issued_at": timezone.now().date(),
    }
