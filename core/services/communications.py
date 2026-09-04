"""
Serviços de comunicações automáticas e notificações institucionais.
Implementa envio de e-mails de boas-vindas com apólice de seguro, alertas de validade e atalhos de WhatsApp.
"""

import logging
import urllib.parse
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from notifications.models import NotificationLog

logger = logging.getLogger(__name__)


def send_athlete_welcome_email(person, request=None) -> bool:
    """
    Envia e-mail institucional de boas-vindas ao atleta com dados da apólice de seguro,
    enquadramento de menores e normas do tapete. Regista o envio no NotificationLog.
    """
    if not person.email:
        logger.info(f"Atleta #{person.pk} ({person.full_name}) não possui endereço de e-mail registado.")
        return False

    subject = f"Bem-vindo(a) à ACR & Proform SC - Inscrição e Apólice de Seguro Desportivo"
    config = getattr(person.organization, 'get_protocol_config', None)
    protocol_config = config() if config else None

    context = {
        'person': person,
        'organization': person.organization,
        'protocol_config': protocol_config,
        'today': timezone.now().date(),
    }

    try:
        html_content = render_to_string('core/emails/welcome_athlete.html', context)
        text_content = strip_tags(html_content)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@acr.local')
        send_mail(
            subject=subject,
            message=text_content,
            from_email=from_email,
            recipient_list=[person.email],
            html_message=html_content,
            fail_silently=False,
        )

        NotificationLog.objects.create(
            person=person,
            channel="email",
            subject=subject,
            status="sent",
            sent_at=timezone.now(),
            detail=f"E-mail de boas-vindas e apólice ({person.insurance_policy or 'Coletiva'}) enviado para {person.email}."
        )
        logger.info(f"E-mail de boas-vindas enviado com sucesso para {person.email}.")
        return True

    except Exception as exc:
        logger.warning(f"Falha ao enviar e-mail de boas-vindas para {person.email}: {exc}")
        NotificationLog.objects.create(
            person=person,
            channel="email",
            subject=subject,
            status="failed",
            sent_at=timezone.now(),
            detail=f"Erro no envio para {person.email}: {str(exc)}"
        )
        return False


def send_insurance_expiry_warning(person) -> bool:
    """
    Envia notificação de aviso quando o seguro desportivo está a expirar ou vencido.
    """
    if not person.email:
        return False

    expiry_str = person.insurance_expiry.strftime('%d/%m/%Y') if person.insurance_expiry else 'indefinida'
    subject = f"Aviso de Regularização: Seguro Desportivo - ACR & Proform SC"
    
    text_content = (
        f"Olá {person.full_name},\n\n"
        f"Informamos que a validade do teu seguro desportivo ({person.insurance_policy or 'Apólice Protocolar'}) "
        f"termina a {expiry_str}.\n"
        f"Para tua proteção e cumprimento das normas desportivas, por favor procede à renovação "
        f"junto da secretaria do Proform SC ou da Direção da ACR.\n\n"
        f"Com os melhores cumprimentos,\n"
        f"ACR & Proform SC"
    )

    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@acr.local')
        send_mail(
            subject=subject,
            message=text_content,
            from_email=from_email,
            recipient_list=[person.email],
            fail_silently=False,
        )

        NotificationLog.objects.create(
            person=person,
            channel="email",
            subject=subject,
            status="sent",
            sent_at=timezone.now(),
            detail=f"Aviso de renovação de seguro ({expiry_str}) enviado com sucesso."
        )
        return True
    except Exception as exc:
        logger.warning(f"Erro ao enviar aviso de seguro para {person.email}: {exc}")
        NotificationLog.objects.create(
            person=person,
            channel="email",
            subject=subject,
            status="failed",
            sent_at=timezone.now(),
            detail=f"Falha ao enviar aviso de seguro: {str(exc)}"
        )
        return False


def get_whatsapp_url(person, message_type: str = "welcome") -> str:
    """
    Gera link do WhatsApp (wa.me) formatado com mensagens pré-definidas para o atleta.
    """
    raw_phone = (person.phone or "").strip().replace(" ", "").replace("-", "").replace(".", "")
    if not raw_phone and person.is_minor and person.guardian_phone:
        raw_phone = (person.guardian_phone or "").strip().replace(" ", "").replace("-", "").replace(".", "")

    if not raw_phone:
        return ""

    # Normalizar prefixo de Portugal se tiver 9 dígitos a começar por 9
    clean_digits = "".join(filter(str.isdigit, raw_phone))
    if len(clean_digits) == 9 and clean_digits.startswith("9"):
        clean_phone = f"351{clean_digits}"
    else:
        clean_phone = clean_digits

    policy_str = person.insurance_policy or "Coletiva ACR"
    expiry_str = person.insurance_expiry.strftime('%d/%m/%Y') if person.insurance_expiry else "em regularização"

    if message_type == "welcome":
        msg = (
            f"Olá {person.first_name}! 👋\n"
            f"Confirmamos a tua inscrição nas atividades desportivas da ACR & Proform SC.\n"
            f"🛡️ Seguro Desportivo: Apólice {policy_str} (Validade: {expiry_str}).\n"
            f"Qualquer dúvida sobre horários e treinos, estamos à tua disposição no balcão!\n"
            f"Bons treinos! 🥋🥊"
        )
    elif message_type == "insurance":
        msg = (
            f"Olá {person.first_name}! ⚠️\n"
            f"Lembramos que o teu seguro desportivo na ACR & Proform SC expira a {expiry_str}.\n"
            f"Para tua segurança no tapete, solicita a renovação na receção do ginásio ou secretaria da ACR. Obrigado!"
        )
    elif message_type == "payment":
        msg = (
            f"Olá {person.first_name}! 💳\n"
            f"Informamos que a mensalidade das tuas atividades desportivas na ACR & Proform SC está disponível para liquidação no Caixa. Obrigado pela preferência!"
        )
    elif message_type == "schedule":
        msg = (
            f"Olá {person.first_name}! 📅\n"
            f"Consulta o horário das aulas e modalidades da ACR & Proform SC. Marca a tua presença no início de cada treino junto do instrutor!"
        )
    else:
        msg = f"Olá {person.first_name}, contacto da ACR & Proform SC."

    return f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
