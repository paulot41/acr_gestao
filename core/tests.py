import json
from datetime import timedelta
from django.test import TestCase, Client, RequestFactory, override_settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.http import HttpResponse
from rest_framework.test import APITestCase

from .models import (
    Organization, Person, Event, Resource, Booking,
    Instructor, Modality, ClassGroup
)
from .middleware import OrganizationMiddleware
from .context_processors import organization_context


class SchedulingRulesTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="acr.local",
            org_type=Organization.Type.BOTH
        )
        self.sala1 = Resource.objects.create(organization=self.org, name="Sala 1", capacity=15)
        self.sala2 = Resource.objects.create(organization=self.org, name="Sala 2", capacity=10)
        self.instructor = Instructor.objects.create(
            organization=self.org,
            first_name="Carlos",
            last_name="Silva",
            email="carlos@example.com"
        )
        self.now = timezone.now().replace(microsecond=0)
        self.start = self.now + timedelta(days=1, hours=10)
        self.end = self.start + timedelta(hours=1)

    def test_resource_overlap_conflict(self):
        """Garante rejeição de duas aulas no mesmo espaço e horário."""
        Event.objects.create(
            organization=self.org,
            resource=self.sala1,
            title="Aula 1",
            starts_at=self.start,
            ends_at=self.end,
            capacity=15,
        )

        # Tentativa de agendar aula sobreposta no mesmo recurso (sala1)
        overlapping_event = Event(
            organization=self.org,
            resource=self.sala1,
            title="Aula Conflituosa",
            starts_at=self.start + timedelta(minutes=15),
            ends_at=self.end + timedelta(minutes=15),
            capacity=15,
        )
        with self.assertRaises(ValidationError) as cm:
            overlapping_event.full_clean()
        self.assertIn("mesmo espaço", str(cm.exception))

    def test_instructor_overlap_conflict(self):
        """Garante rejeição do mesmo instrutor em duas salas no mesmo horário."""
        Event.objects.create(
            organization=self.org,
            resource=self.sala1,
            instructor=self.instructor,
            title="Aula Sala 1",
            starts_at=self.start,
            ends_at=self.end,
            capacity=15,
        )

        # Tentativa do mesmo instrutor na sala2 ao mesmo tempo
        overlapping_instructor_event = Event(
            organization=self.org,
            resource=self.sala2,
            instructor=self.instructor,
            title="Aula Sala 2",
            starts_at=self.start + timedelta(minutes=30),
            ends_at=self.end + timedelta(minutes=30),
            capacity=10,
        )
        with self.assertRaises(ValidationError) as cm:
            overlapping_instructor_event.full_clean()
        self.assertIn("instrutor", str(cm.exception).lower())

    def test_event_chronology(self):
        """Garante que ends_at deve ser posterior a starts_at."""
        event = Event(
            organization=self.org,
            resource=self.sala1,
            title="Aula Temporal Inválida",
            starts_at=self.end,
            ends_at=self.start,  # Fim antes do início
            capacity=10,
        )
        with self.assertRaises(ValidationError) as cm:
            event.full_clean()
        self.assertIn("must be after starts_at", str(cm.exception))

    def test_class_group_capacity(self):
        """Valida a correta atribuição de capacidade com base na turma associada."""
        modality = Modality.objects.create(
            organization=self.org,
            name="Pilates Clínico",
            entity_type="proform"
        )
        class_group = ClassGroup.objects.create(
            organization=self.org,
            modality=modality,
            name="Turma A",
            max_students=8
        )
        event = Event(
            organization=self.org,
            resource=self.sala2,
            event_type=Event.EventType.GROUP_CLASS,
            class_group=class_group,
            title="Aula Turma A",
            starts_at=self.start,
            ends_at=self.end,
            capacity=0,  # Não especificado manualmente
        )
        event.full_clean()
        event.save()
        self.assertEqual(event.capacity, 8)
        self.assertEqual(event.max_capacity, 8)


@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class OrganizationMiddlewareTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="acr.local",
            org_type=Organization.Type.BOTH,
            gym_monthly_fee=35.00,
            wellness_monthly_fee=50.00
        )

    def test_organization_fallback(self):
        """Garante que acessos via IP de rede local ou domínio desconhecido não dão 404 e usam a organização padrão."""
        middleware = OrganizationMiddleware(lambda req: HttpResponse("OK"))

        # Simular request a partir de um IP de rede local
        request = self.factory.get("/", HTTP_HOST="192.168.1.150:8000")
        response = middleware(request)

        self.assertIsNotNone(request.organization)
        self.assertEqual(request.organization.name, "ACR & Proform SC")
        self.assertEqual(request.org_settings["gym_fee"], 35.0)
        self.assertEqual(response["X-Organization-Domain"], "acr.local")

    def test_organization_fallback_creates_default_if_none_exist(self):
        """Se nenhuma organização existir, o middleware cria a organização unificada padrão."""
        Organization.objects.all().delete()

        middleware = OrganizationMiddleware(lambda req: HttpResponse("OK"))
        request = self.factory.get("/", HTTP_HOST="novahost.local")
        response = middleware(request)

        self.assertIsNotNone(request.organization)
        self.assertEqual(request.organization.name, "ACR & Proform SC")
        self.assertEqual(request.organization.org_type, Organization.Type.BOTH)
        self.assertEqual(response["X-Organization-Type"], "both")

    def test_organization_context_processor(self):
        """Valida que o context processor injeta a organização e org_settings nos templates."""
        request = self.factory.get("/")
        request.organization = self.org
        request.org_settings = {
            "gym_fee": 35.0,
            "wellness_fee": 50.0,
            "org_name": self.org.name
        }
        context = organization_context(request)
        self.assertEqual(context["organization"], self.org)
        self.assertEqual(context["org_settings"]["gym_fee"], 35.0)


@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class GanttAPITestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="testserver",
            org_type=Organization.Type.BOTH
        )
        self.user = User.objects.create_superuser(username="admin", password="password123", email="admin@test.com")
        self.client = Client()
        self.client.login(username="admin", password="password123")

        self.resource1 = Resource.objects.create(organization=self.org, name="Estúdio 1", capacity=12)
        self.resource2 = Resource.objects.create(organization=self.org, name="Estúdio 2", capacity=10)
        self.instructor = Instructor.objects.create(
            organization=self.org,
            first_name="Rui",
            last_name="Costa",
            email="rui@test.com"
        )
        self.now = timezone.now().replace(microsecond=0)
        self.date_str = (self.now + timedelta(days=2)).strftime("%Y-%m-%d")

    def test_gantt_create_event_instructor_conflict(self):
        """Gantt API deve rejeitar aula quando o mesmo instrutor já está ocupado no horário."""
        # Criar primeira aula com o instrutor no recurso 1 das 10:00 às 11:00
        payload1 = {
            "resource_id": self.resource1.id,
            "instructor_id": self.instructor.id,
            "date": self.date_str,
            "start_time": "10:00",
            "end_time": "11:00"
        }
        res1 = self.client.post(
            "/gantt/create-event/",
            data=json.dumps(payload1),
            content_type="application/json"
        )
        self.assertEqual(res1.status_code, 200)

        # Tentativa de criar segunda aula com o mesmo instrutor no recurso 2 das 10:30 às 11:30
        payload2 = {
            "resource_id": self.resource2.id,
            "instructor_id": self.instructor.id,
            "date": self.date_str,
            "start_time": "10:30",
            "end_time": "11:30"
        }
        res2 = self.client.post(
            "/gantt/create-event/",
            data=json.dumps(payload2),
            content_type="application/json"
        )
        self.assertEqual(res2.status_code, 400)
        data = res2.json()
        self.assertIn("já tem uma aula agendada", data.get("error", ""))

    def test_validate_event_conflict_api(self):
        """API validate-conflict deve reportar conflitos de recurso e de instrutor especificamente."""
        # Criar evento base
        start_dt = timezone.make_aware(timezone.datetime.strptime(f"{self.date_str} 14:00", "%Y-%m-%d %H:%M"))
        end_dt = timezone.make_aware(timezone.datetime.strptime(f"{self.date_str} 15:00", "%Y-%m-%d %H:%M"))
        Event.objects.create(
            organization=self.org,
            resource=self.resource1,
            instructor=self.instructor,
            title="Aula Pilates",
            starts_at=start_dt,
            ends_at=end_dt,
            capacity=10
        )

        # Validar conflito de recurso
        conflict_payload_res = {
            "resource_id": self.resource1.id,
            "starts_at": f"{self.date_str}T14:15:00",
            "ends_at": f"{self.date_str}T15:15:00"
        }
        res_conflict = self.client.post(
            "/api/validate-conflict/",
            data=json.dumps(conflict_payload_res),
            content_type="application/json"
        )
        self.assertEqual(res_conflict.status_code, 200)
        data_res = res_conflict.json()
        self.assertTrue(data_res["has_conflict"])
        self.assertEqual(data_res["conflict_type"], "resource")

        # Validar conflito de instrutor em outro recurso
        conflict_payload_inst = {
            "resource_id": self.resource2.id,
            "instructor_id": self.instructor.id,
            "starts_at": f"{self.date_str}T14:15:00",
            "ends_at": f"{self.date_str}T15:15:00"
        }
        res_inst_conflict = self.client.post(
            "/api/validate-conflict/",
            data=json.dumps(conflict_payload_inst),
            content_type="application/json"
        )
        self.assertEqual(res_inst_conflict.status_code, 200)
        data_inst = res_inst_conflict.json()
        self.assertTrue(data_inst["has_conflict"])
        self.assertEqual(data_inst["conflict_type"], "instructor")

    def test_csrf_protection_on_gantt_post(self):
        """Garante que requisições POST nos endpoints do Gantt sem CSRF token são rejeitadas quando CSRF é forçado."""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="admin", password="password123")

        payload = {
            "resource_id": self.resource1.id,
            "date": self.date_str,
            "start_time": "16:00",
            "end_time": "17:00"
        }
        # Tentativa de POST sem CSRF token
        res_no_csrf = csrf_client.post(
            "/gantt/create-event/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res_no_csrf.status_code, 403)


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
