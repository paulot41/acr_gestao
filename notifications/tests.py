from django.test import TestCase
from django.utils import timezone
from core.models import Organization, Person
from .models import Template, Campaign, NotificationLog


class NotificationModelsTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org", domain="org.com")
        self.template = Template.objects.create(name="Temp", subject="Sub", body="Body")

    def test_campaign_creation(self):
        campaign = Campaign.objects.create(organization=self.org, name="Camp", template=self.template)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(campaign.template.subject, "Sub")

    def test_notification_log(self):
        campaign = Campaign.objects.create(organization=self.org, name="Camp", template=self.template)
        person = Person.objects.create(organization=self.org, first_name="Ana", email="ana@example.com", nif="1")
        log = NotificationLog.objects.create(campaign=campaign, person=person)
        log.mark_sent()
        self.assertEqual(log.status, "sent")
        self.assertIsNotNone(log.sent_at)
