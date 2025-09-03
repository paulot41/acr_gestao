from django.test import TestCase
from rest_framework.test import APITestCase
from .models import Organization, Person, Event


class EventAPITestCase(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")

    def test_event_creation(self):
        # Testar criação de eventos via API
        pass

    def test_booking_capacity(self):
        # Testar limite de capacidade
        pass