from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Campaign, NotificationLog
from core.models import Person


def _send_email(to_email: str, subject: str, body: str):
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])


def _send_sms(to_number: str, body: str):  # pragma: no cover - placeholder
    print(f"Sending SMS to {to_number}: {body}")


@shared_task
def send_campaign(campaign_id: int) -> int:
    campaign = Campaign.objects.get(pk=campaign_id)
    template = campaign.template
    if campaign.channel == "sms":
        recipients = Person.objects.filter(
            organization=campaign.organization,
            marketing_optin_sms=True,
            consent_rgpd=True,
        ).exclude(phone="").values_list("id", "phone")
    else:
        recipients = Person.objects.filter(
            organization=campaign.organization,
            marketing_optin_email=True,
            consent_rgpd=True,
        ).exclude(email="").values_list("id", "email")
    count = 0
    for person_id, contact in recipients:
        try:
            if campaign.channel == "sms":
                _send_sms(contact, template.body)
            else:
                _send_email(contact, template.subject, template.body)
            NotificationLog.objects.create(
                campaign=campaign,
                person_id=person_id,
                status="sent",
                channel=campaign.channel,
            )
            count += 1
        except Exception as exc:  # pragma: no cover - log error
            NotificationLog.objects.create(
                campaign=campaign,
                person_id=person_id,
                status="failed",
                channel=campaign.channel,
                detail=str(exc),
            )
    return count
