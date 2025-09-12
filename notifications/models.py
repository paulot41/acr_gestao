from django.db import models
from django.utils import timezone
from core.models import Organization, Person


class Template(models.Model):
    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
    ]
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="email")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Campaign(models.Model):
    CHANNEL_CHOICES = Template.CHANNEL_CHOICES
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="email")
    scheduled_for = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class NotificationLog(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pendente"),
        ("sent", "Enviado"),
        ("failed", "Falhou"),
    ]
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="logs")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    channel = models.CharField(max_length=10, choices=Campaign.CHANNEL_CHOICES, default="email")
    sent_at = models.DateTimeField(null=True, blank=True)
    detail = models.TextField(blank=True)

    def mark_sent(self, detail: str = ""):
        self.status = "sent"
        self.sent_at = timezone.now()
        self.detail = detail
        self.save(update_fields=["status", "sent_at", "detail"])

    def __str__(self) -> str:
        return f"{self.campaign.name} -> {self.person} ({self.status})"
