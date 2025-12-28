from rest_framework.test import APITestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Organization, Person, Event, Resource, Booking


class EventAPITestCase(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org", domain="test.org")
        self.resource = Resource.objects.create(organization=self.org, name="Sala 1", capacity=1)

    def test_event_creation(self):
        """Criar evento simples e confirmar valores."""
        event = Event.objects.create(
            organization=self.org,
            resource=self.resource,
            title="Treino",
            starts_at=timezone.now(),
            ends_at=timezone.now() + timezone.timedelta(hours=1),
            capacity=1,
        )
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(event.title, "Treino")

    def test_booking_capacity(self):
        """Não permitir reservas além da capacidade."""
        event = Event.objects.create(
            organization=self.org,
            resource=self.resource,
            title="Treino",
            starts_at=timezone.now(),
            ends_at=timezone.now() + timezone.timedelta(hours=1),
            capacity=1,
        )
        p1, p2 = Person.objects.bulk_create([
            Person(organization=self.org, first_name="Ana", email="ana@example.com", nif="1"),
            Person(organization=self.org, first_name="Bea", email="bea@example.com", nif="2"),
        ])

        b1 = Booking(organization=self.org, event=event, person=p1)
        b1.save()

        b2 = Booking(organization=self.org, event=event, person=p2)
        with self.assertRaises(ValidationError):
            b2.full_clean()


class PersonConsentTestCase(APITestCase):
    def test_rgpd_consent_default(self):
        org = Organization.objects.create(name="Org", domain="org.com")
        person = Person.objects.create(
            organization=org,
            first_name="Ana",
            email="ana@example.com",
            nif="1",
        )
        self.assertFalse(person.consent_rgpd)

    def test_rgpd_consent_set_true(self):
        org = Organization.objects.create(name="Org", domain="org.com")
        person = Person.objects.create(
            organization=org,
            first_name="Ana",
            email="ana@example.com",
            nif="1",
            consent_rgpd=True,
        )
        self.assertTrue(person.consent_rgpd)
