import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase, Client, RequestFactory, override_settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.urls import reverse
from rest_framework.test import APITestCase

from django.core import mail
from notifications.models import NotificationLog

import unittest.mock
from django.db import DatabaseError
from django.db.models import ProtectedError
from django.contrib.messages import get_messages

from .models import (
    Organization, Person, Event, Resource, Booking,
    Instructor, Modality, ClassGroup, PaymentPlan,
    ClientSubscription, CreditHistory, Payment, GoogleDriveSyncLog,
    InstructorCommission, ProtocolPeriodSettlement, ProtocolConfiguration,
    AthleteGraduation, GoverningBody, GoverningBodyMember,
    UserProfile, Invoice
)
from .middleware import OrganizationMiddleware
from .context_processors import organization_context
from .services.kiosk import resolve_person, process_kiosk_checkin, get_active_event_for_facility
from .services.membership_card import get_membership_card_data
from .services.bookings import cancel_booking
from .services.scheduling import ensure_capacity, ensure_no_conflict


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


class AthleteFrontofficeTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="acr.local",
            org_type=Organization.Type.BOTH
        )

    def test_athlete_is_minor(self):
        """Valida deteção automática de menores de 18 anos."""
        today = timezone.now().date()
        # Menor de idade (12 anos)
        minor = Person.objects.create(
            organization=self.org,
            first_name="Pedro",
            last_name="Santos",
            date_of_birth=today - timedelta(days=12 * 365),
            guardian_name="Teresa Santos",
            guardian_phone="912345678",
            guardian_nif="123456789"
        )
        self.assertTrue(minor.is_minor)
        self.assertEqual(minor.guardian_name, "Teresa Santos")

        # Maior de idade (25 anos)
        adult = Person.objects.create(
            organization=self.org,
            first_name="Rui",
            last_name="Martins",
            date_of_birth=today - timedelta(days=25 * 365)
        )
        self.assertFalse(adult.is_minor)

        # Sem data de nascimento
        unknown = Person.objects.create(
            organization=self.org,
            first_name="Desconhecido",
            last_name="Silva"
        )
        self.assertFalse(unknown.is_minor)

    def test_athlete_insurance_status(self):
        """Valida badges e estados do seguro desportivo."""
        today = timezone.now().date()

        # Válido (> 30 dias)
        valid_athlete = Person.objects.create(
            organization=self.org,
            first_name="Atleta",
            last_name="Valido",
            insurance_policy="AP-12345",
            insurance_expiry=today + timedelta(days=90)
        )
        self.assertEqual(valid_athlete.insurance_status['status'], 'valid')
        self.assertTrue(valid_athlete.insurance_status['is_valid'])

        # A expirar em breve (<= 30 dias)
        expiring_athlete = Person.objects.create(
            organization=self.org,
            first_name="Atleta",
            last_name="Expirando",
            insurance_expiry=today + timedelta(days=15)
        )
        self.assertEqual(expiring_athlete.insurance_status['status'], 'expiring_soon')
        self.assertTrue(expiring_athlete.insurance_status['is_valid'])

        # Vencido
        expired_athlete = Person.objects.create(
            organization=self.org,
            first_name="Atleta",
            last_name="Vencido",
            insurance_expiry=today - timedelta(days=5)
        )
        self.assertEqual(expired_athlete.insurance_status['status'], 'expired')
        self.assertFalse(expired_athlete.insurance_status['is_valid'])

        # Sem seguro
        missing_athlete = Person.objects.create(
            organization=self.org,
            first_name="Atleta",
            last_name="SemSeguro"
        )
        self.assertEqual(missing_athlete.insurance_status['status'], 'missing')
        self.assertFalse(missing_athlete.insurance_status['is_valid'])

    def test_athlete_medical_status(self):
        """Valida estados do atestado/exame médico."""
        today = timezone.now().date()

        athlete = Person.objects.create(
            organization=self.org,
            first_name="Atleta",
            last_name="Medico",
            medical_certificate_expiry=today + timedelta(days=45)
        )
        self.assertEqual(athlete.medical_status['status'], 'valid')
        self.assertTrue(athlete.medical_status['is_valid'])

        athlete.medical_certificate_expiry = today - timedelta(days=2)
        athlete.save()
        self.assertEqual(athlete.medical_status['status'], 'expired')
        self.assertFalse(athlete.medical_status['is_valid'])


@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class CashierAndPaymentsTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="testserver",
            org_type=Organization.Type.BOTH
        )
        self.user = User.objects.create_superuser(
            username="reception",
            password="password123",
            email="reception@acr.local"
        )
        self.client = Client()
        self.client.login(username="reception", password="password123")

        self.athlete = Person.objects.create(
            organization=self.org,
            first_name="Gonçalo",
            last_name="Neves",
            email="goncalo@example.com",
            nif="234567890"
        )
        self.monthly_plan = PaymentPlan.objects.create(
            organization=self.org,
            name="Mensalidade Jiu-Jitsu",
            plan_type=PaymentPlan.PlanType.MONTHLY,
            price=50.00,
            duration_months=1,
            is_active=True
        )
        self.credits_plan = PaymentPlan.objects.create(
            organization=self.org,
            name="Pack 10 Aulas Boxe",
            plan_type=PaymentPlan.PlanType.CREDITS,
            price=60.00,
            credits_included=10,
            credits_validity_days=60,
            is_active=True
        )

    def test_cashier_dashboard_view(self):
        """Garante acesso ao painel de caixa e carregamento dos totais por método."""
        res = self.client.get("/cashier/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("total_today", res.context)
        self.assertIn("cash_today", res.context)

    def test_payment_registration_with_monthly_plan(self):
        """Registo de pagamento de mensalidade no balcão deve criar Payment e ClientSubscription ativa."""
        today_str = timezone.now().date().strftime("%Y-%m-%d")
        payload = {
            "person": self.athlete.pk,
            "payment_plan": self.monthly_plan.pk,
            "amount": "50.00",
            "method": "mbway",
            "paid_date": today_str,
            "auto_activate": "on",
            "description": "Mensalidade Setembro"
        }
        res = self.client.post("/payments/add/", data=payload, follow=True)
        self.assertEqual(res.status_code, 200)

        # Pagamento criado
        payment = Payment.objects.filter(person=self.athlete, amount=50.00).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.method, "mbway")

        # Subscrição criada e marcada como paga
        sub = ClientSubscription.objects.filter(person=self.athlete, payment_plan=self.monthly_plan).first()
        self.assertIsNotNone(sub)
        self.assertTrue(sub.is_paid)
        self.assertEqual(sub.status, ClientSubscription.Status.ACTIVE)

    def test_payment_registration_with_credits_pack(self):
        """Registo de pack de créditos carrega créditos e regista histórico em CreditHistory."""
        today_str = timezone.now().date().strftime("%Y-%m-%d")
        payload = {
            "person": self.athlete.pk,
            "payment_plan": self.credits_plan.pk,
            "amount": "60.00",
            "method": "cash",
            "paid_date": today_str,
            "auto_activate": "on"
        }
        res = self.client.post("/payments/add/", data=payload, follow=True)
        self.assertEqual(res.status_code, 200)

        # Subscrição de créditos com saldo de 10
        sub = ClientSubscription.objects.filter(person=self.athlete, payment_plan=self.credits_plan).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.remaining_credits, 10)

        # Histórico de créditos criado
        history = CreditHistory.objects.filter(person=self.athlete, action=CreditHistory.Action.PURCHASE).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.credits_amount, 10)
        self.assertEqual(history.credits_after, 10)

    def test_payment_receipt_view(self):
        """Garante emissão do comprovativo/recibo com dados do atleta e organização."""
        payment = Payment.objects.create(
            organization=self.org,
            person=self.athlete,
            amount=50.00,
            method="card",
            paid_date=timezone.now().date(),
            description="Quota + Mensalidade"
        )
        res = self.client.get(f"/payments/{payment.pk}/receipt/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "RECIBO / COMPROVATIVO")
        self.assertContains(res, self.athlete.first_name)
        self.assertContains(res, "50,00")

    def test_client_subscribe_view(self):
        """Garante atribuição direta de plano ao atleta no frontoffice."""
        today_str = timezone.now().date().strftime("%Y-%m-%d")
        payload = {
            "payment_plan": self.monthly_plan.pk,
            "start_date": today_str,
            "is_paid": "on",
            "notes": "Atribuição no balcão"
        }
        res = self.client.post(f"/clients/{self.athlete.pk}/subscribe/", data=payload, follow=True)
        self.assertEqual(res.status_code, 200)

        sub = ClientSubscription.objects.filter(person=self.athlete, payment_plan=self.monthly_plan).first()
        self.assertIsNotNone(sub)
        self.assertTrue(sub.is_paid)


@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class CommunicationsTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="acr.local",
            org_type=Organization.Type.BOTH
        )
        self.athlete = Person.objects.create(
            organization=self.org,
            first_name="Tiago",
            last_name="Ribeiro",
            email="tiago@example.com",
            phone="919998877",
            insurance_policy="AP-998877",
            insurance_expiry=timezone.now().date() + timedelta(days=180)
        )
        self.minor = Person.objects.create(
            organization=self.org,
            first_name="Martim",
            last_name="Ribeiro",
            date_of_birth=timezone.now().date() - timedelta(days=10 * 365),
            guardian_name="Tiago Ribeiro",
            guardian_phone="919998877",
            guardian_nif="123123123"
        )
        self.user = User.objects.create_superuser(username="admin_comm", password="password123", email="admin@acr.local")
        self.client = Client()
        self.client.login(username="admin_comm", password="password123")

    def test_send_athlete_welcome_email(self):
        """Valida envio de e-mail de boas-vindas com apólice de seguro e registo em NotificationLog."""
        from core.services.communications import send_athlete_welcome_email
        success = send_athlete_welcome_email(self.athlete)
        self.assertTrue(success)

        # Verificar e-mail na outbox do Django
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn("ACR & Proform SC", sent_email.subject)
        self.assertIn(self.athlete.email, sent_email.to)
        self.assertIn("AP-998877", sent_email.body)

        # Verificar NotificationLog
        log = NotificationLog.objects.filter(person=self.athlete).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, "sent")
        self.assertEqual(log.channel, "email")

    def test_send_athlete_welcome_email_no_email(self):
        """Atleta sem e-mail não deve provocar erro e deve retornar False."""
        from core.services.communications import send_athlete_welcome_email
        athlete_no_email = Person.objects.create(
            organization=self.org,
            first_name="Sem",
            last_name="Email"
        )
        self.assertFalse(send_athlete_welcome_email(athlete_no_email))

    def test_get_whatsapp_url(self):
        """Valida geração de links universais do WhatsApp com mensagens pré-formatadas."""
        from core.services.communications import get_whatsapp_url
        url_welcome = get_whatsapp_url(self.athlete, "welcome")
        self.assertIn("https://wa.me/351919998877", url_welcome)
        self.assertIn("Seguro", url_welcome)

        url_minor = get_whatsapp_url(self.minor, "welcome")
        self.assertIn("https://wa.me/351919998877", url_minor)

    def test_client_resend_welcome_view(self):
        """Garante funcionamento do botão de reenvio de e-mail na ficha do atleta."""
        res = self.client.get(f"/clients/{self.athlete.pk}/resend-welcome/", follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "reenviado com sucesso")
        self.assertTrue(len(mail.outbox) >= 1)


@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class GoogleDriveSyncTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="testserver",
            org_type=Organization.Type.BOTH
        )
        self.user = User.objects.create_superuser(username="admin_drive", password="password123", email="drive@acr.local")
        self.client = Client()
        self.client.login(username="admin_drive", password="password123")

        self.athlete = Person.objects.create(
            organization=self.org,
            first_name="Bruno",
            last_name="Alves",
            email="bruno@example.com",
            nif="111222333",
            insurance_policy="AP-554433",
            insurance_expiry=timezone.now().date() + timedelta(days=60)
        )

    def test_generate_athletes_excel(self):
        """Valida criação da folha de cálculo Excel (.xlsx) dos praticantes com openpyxl."""
        from core.services.google_drive import generate_athletes_excel
        excel_bytes = generate_athletes_excel(self.org)
        self.assertTrue(len(excel_bytes) > 1000)
        # Assinatura zip/xlsx (PK\x03\x04)
        self.assertTrue(excel_bytes.startswith(b'PK'))

    def test_generate_athletes_csv(self):
        """Valida exportação CSV da lista oficial de atletas."""
        from core.services.google_drive import generate_athletes_csv
        csv_str = generate_athletes_csv(self.org)
        self.assertIn("Bruno Alves", csv_str)
        self.assertIn("AP-554433", csv_str)
        self.assertIn("Apólice Seguro", csv_str)

    def test_google_drive_sync_view(self):
        """Garante acesso ao painel de controlo da Google Drive."""
        res = self.client.get("/google-drive/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Sincronização Google Drive da ACR")
        self.assertIn("total_athletes", res.context)

    def test_google_drive_trigger_sync_and_log(self):
        """Disparo manual de sincronização deve registar histórico em GoogleDriveSyncLog."""
        res = self.client.post("/google-drive/sync/", follow=True)
        self.assertEqual(res.status_code, 200)

        log = GoogleDriveSyncLog.objects.filter(organization=self.org).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.athletes_count, 1)
        self.assertEqual(log.status, GoogleDriveSyncLog.Status.SUCCESS)

    def test_export_athletes_sheet_view(self):
        """Garante download direto das planilhas em Excel e CSV."""
        res_xlsx = self.client.get("/google-drive/export/?format=xlsx")
        self.assertEqual(res_xlsx.status_code, 200)
        self.assertEqual(res_xlsx["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        res_csv = self.client.get("/google-drive/export/?format=csv")
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn("text/csv", res_csv["Content-Type"])


@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class MatCheckinTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="testserver",
            org_type=Organization.Type.BOTH
        )
        self.user = User.objects.create_superuser(username="instructor_mat", password="password123", email="coach@acr.local")
        self.client = Client()
        self.client.login(username="instructor_mat", password="password123")

        self.modality = Modality.objects.create(
            organization=self.org,
            name="Jiu-Jitsu",
            color="#0d6efd"
        )
        self.resource = Resource.objects.create(
            organization=self.org,
            name="Tatami Principal",
            capacity=20
        )
        self.instructor = Instructor.objects.create(
            organization=self.org,
            first_name="Mestre",
            last_name="Silva"
        )
        now = timezone.now().replace(microsecond=0)
        self.event = Event.objects.create(
            organization=self.org,
            modality=self.modality,
            resource=self.resource,
            instructor=self.instructor,
            title="Jiu-Jitsu Avançado",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
            capacity=20
        )

        # Atleta 1 (com mensalidade ativa)
        self.athlete_monthly = Person.objects.create(
            organization=self.org,
            first_name="Duarte",
            last_name="Ferreira",
            email="duarte@example.com"
        )
        self.plan_monthly = PaymentPlan.objects.create(
            organization=self.org,
            name="Mensalidade Livre",
            plan_type=PaymentPlan.PlanType.MONTHLY,
            price=45.0,
            duration_months=1,
            is_active=True
        )
        self.sub_monthly = ClientSubscription.objects.create(
            organization=self.org,
            person=self.athlete_monthly,
            payment_plan=self.plan_monthly,
            status=ClientSubscription.Status.ACTIVE,
            start_date=now.date(),
            end_date=now.date() + timedelta(days=30),
            is_paid=True
        )

        # Atleta 2 (com pacote de créditos)
        self.athlete_credits = Person.objects.create(
            organization=self.org,
            first_name="Diogo",
            last_name="Melo",
            email="diogo@example.com"
        )
        self.plan_credits = PaymentPlan.objects.create(
            organization=self.org,
            name="Pack 10",
            plan_type=PaymentPlan.PlanType.CREDITS,
            price=60.0,
            credits_included=10,
            credits_validity_days=60,
            is_active=True
        )
        self.sub_credits = ClientSubscription.objects.create(
            organization=self.org,
            person=self.athlete_credits,
            payment_plan=self.plan_credits,
            status=ClientSubscription.Status.ACTIVE,
            start_date=now.date(),
            end_date=now.date() + timedelta(days=60),
            remaining_credits=5,
            is_paid=True
        )

        # Reserva inicial do atleta mensal
        self.booking_monthly = Booking.objects.create(
            organization=self.org,
            event=self.event,
            person=self.athlete_monthly,
            status=Booking.Status.CONFIRMED
        )

    def test_event_checkin_view(self):
        """Garante acesso ao ecrã de check-in no tapete e listagem de participantes."""
        res = self.client.get(f"/events/{self.event.pk}/checkin/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Check-in no Tapete")
        self.assertContains(res, self.event.title)
        self.assertContains(res, self.athlete_monthly.full_name)

    def test_booking_toggle_checkin(self):
        """Garante alternância rápida de presença (Presente, Falta, Pendente) com 1 toque."""
        # Marcar Presente
        res_present = self.client.post(
            f"/bookings/{self.booking_monthly.pk}/toggle-checkin/",
            data={"status": "checked_in"},
            follow=True
        )
        self.assertEqual(res_present.status_code, 200)
        self.booking_monthly.refresh_from_db()
        self.assertEqual(self.booking_monthly.status, Booking.Status.CHECKED_IN)

        # Marcar Falta
        res_noshow = self.client.post(
            f"/bookings/{self.booking_monthly.pk}/toggle-checkin/",
            data={"status": "no_show"},
            follow=True
        )
        self.assertEqual(res_noshow.status_code, 200)
        self.booking_monthly.refresh_from_db()
        self.assertEqual(self.booking_monthly.status, Booking.Status.NO_SHOW)

    def test_event_quick_add_attendance_credits(self):
        """Adição de atleta com créditos no tapete consome 1 crédito e cria histórico em CreditHistory."""
        res = self.client.post(
            f"/events/{self.event.pk}/quick-add/",
            data={"person_id": self.athlete_credits.pk},
            follow=True
        )
        self.assertEqual(res.status_code, 200)

        # Booking criado como checked_in
        booking = Booking.objects.filter(event=self.event, person=self.athlete_credits).first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.status, Booking.Status.CHECKED_IN)

        # Crédito consumido (de 5 para 4)
        self.sub_credits.refresh_from_db()
        self.assertEqual(self.sub_credits.remaining_credits, 4)

        # Histórico de débito de créditos criado
        history = CreditHistory.objects.filter(
            person=self.athlete_credits,
            action=CreditHistory.Action.USE
        ).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.credits_amount, -1)
        self.assertEqual(history.credits_after, 4)


@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class ProtocolFinanceTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="testserver",
            org_type=Organization.Type.BOTH
        )
        self.user = User.objects.create_superuser(username="admin_finance", password="password123", email="fin@acr.local")
        self.client = Client()
        self.client.login(username="admin_finance", password="password123")

        self.today = timezone.now().date()
        self.start_date = self.today.replace(day=1)
        self.end_date = self.today

        # Modalidades
        self.mod_jj = Modality.objects.create(organization=self.org, name="Jiu-Jitsu", entity_type="acr")
        self.mod_boxe = Modality.objects.create(organization=self.org, name="Boxe", entity_type="both")

        # Espaço
        self.dojo = Resource.objects.create(organization=self.org, name="Dojo Central", capacity=20)

        # Instrutores
        self.inst_carlos = Instructor.objects.create(
            organization=self.org,
            first_name="Carlos",
            last_name="Gracie",
            email="carlos@example.com",
            entity_affiliation=Instructor.EntityAffiliation.ACR_ONLY,
            acr_commission_rate=60.00
        )
        self.inst_miguel = Instructor.objects.create(
            organization=self.org,
            first_name="Miguel",
            last_name="Santos",
            email="miguel@example.com",
            entity_affiliation=Instructor.EntityAffiliation.PROFORM_ONLY,
            proform_commission_rate=70.00
        )

        # Praticantes
        self.ath_acr = Person.objects.create(
            organization=self.org,
            first_name="Andre",
            last_name="Costa",
            entity_affiliation=Person.EntityAffiliation.ACR_ONLY
        )
        self.ath_proform = Person.objects.create(
            organization=self.org,
            first_name="Paula",
            last_name="Lima",
            entity_affiliation=Person.EntityAffiliation.PROFORM_ONLY
        )
        self.ath_both = Person.objects.create(
            organization=self.org,
            first_name="Joao",
            last_name="Neves",
            entity_affiliation=Person.EntityAffiliation.BOTH
        )

        # Pagamentos registados e concluídos
        Payment.objects.create(
            organization=self.org,
            person=self.ath_acr,
            amount=Decimal("100.00"),
            status=Payment.Status.COMPLETED,
            paid_date=self.today
        )
        Payment.objects.create(
            organization=self.org,
            person=self.ath_proform,
            amount=Decimal("150.00"),
            status=Payment.Status.COMPLETED,
            paid_date=self.today
        )
        Payment.objects.create(
            organization=self.org,
            person=self.ath_both,
            amount=Decimal("250.00"),
            status=Payment.Status.COMPLETED,
            paid_date=self.today
        )

        # Aulas lecionadas
        starts = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        self.event_jj = Event.objects.create(
            organization=self.org,
            modality=self.mod_jj,
            instructor=self.inst_carlos,
            resource=self.dojo,
            title="Treino Jiu-Jitsu",
            starts_at=starts,
            ends_at=starts + timedelta(hours=1),
            capacity=20
        )
        self.event_boxe = Event.objects.create(
            organization=self.org,
            modality=self.mod_boxe,
            instructor=self.inst_miguel,
            resource=self.dojo,
            title="Treino Boxe",
            starts_at=starts + timedelta(hours=2),
            ends_at=starts + timedelta(hours=3),
            capacity=20
        )

        # Presenças no tapete
        Booking.objects.create(
            organization=self.org,
            event=self.event_jj,
            person=self.ath_acr,
            status=Booking.Status.CHECKED_IN
        )
        Booking.objects.create(
            organization=self.org,
            event=self.event_boxe,
            person=self.ath_both,
            status=Booking.Status.CHECKED_IN
        )

    def test_protocol_split_calculation_integrity(self):
        """Valida que a receita bruta é dividida estritamente sem perda de cêntimos:
           Receita Bruta = Remuneração Instrutores + Proform SC + ACR."""
        from core.services.protocol_finance import calculate_period_protocol_split
        split = calculate_period_protocol_split(self.org, self.start_date, self.end_date)

        gross = split['gross_revenue']
        self.assertEqual(gross, Decimal("500.00"))
        self.assertEqual(split['acr_only_revenue'], Decimal("100.00"))
        self.assertEqual(split['proform_only_revenue'], Decimal("150.00"))
        self.assertEqual(split['joint_revenue'], Decimal("250.00"))

        # Integridade estrita: soma das 3 partes deve ser rigorosamente igual a gross_revenue
        inst_total = split['instructors_total']
        proform_share = split['proform_share']
        acr_share = split['acr_share']
        self.assertEqual(gross, inst_total + proform_share + acr_share)

        # Margem líquida
        self.assertEqual(split['net_entity_margin'], gross - inst_total)
        self.assertTrue(len(split['instructors_breakdown']) == 2)
        self.assertTrue(len(split['modality_breakdown']) == 2)

    def test_create_or_update_period_settlement(self):
        """Gera e persiste fecho de contas oficial com integridade de valores."""
        from core.services.protocol_finance import create_or_update_period_settlement
        settlement = create_or_update_period_settlement(
            self.org, self.start_date, self.end_date, notes="Acordo validado mensal"
        )
        self.assertIsNotNone(settlement.pk)
        self.assertEqual(settlement.status, ProtocolPeriodSettlement.Status.DRAFT)
        self.assertEqual(settlement.total_revenue, Decimal("500.00"))
        self.assertEqual(
            settlement.total_revenue,
            settlement.instructor_total + settlement.proform_share + settlement.acr_share
        )

        # Atualização subsequente do mesmo fecho no mesmo período não cria duplicados
        updated = create_or_update_period_settlement(
            self.org, self.start_date, self.end_date, notes="Nova observação"
        )
        self.assertEqual(settlement.pk, updated.pk)
        self.assertEqual(updated.notes, "Nova observação")

    def test_protocol_supervision_views(self):
        """Testa o portal de supervisão, emissão de fecho e visualização de declaração oficial."""
        # 1. Acesso ao painel de supervisão
        res = self.client.get("/protocol/supervision/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Supervisão do Protocolo ACR & Proform SC")
        self.assertContains(res, "Receita Bruta Total")
        self.assertContains(res, "Equilíbrio Estrito da Partilha Tripartida")
        self.assertContains(res, "Carlos Gracie")

        # 2. Criar fecho de contas via POST
        res_create = self.client.post("/protocol/settlement/create/", data={
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "notes": "Fecho Oficial Trimestral"
        }, follow=True)
        self.assertEqual(res_create.status_code, 200)
        self.assertContains(res_create, "Declaração de Fecho de Contas")

        settlement = ProtocolPeriodSettlement.objects.filter(organization=self.org).first()
        self.assertIsNotNone(settlement)

        # 3. Visualizar declaração oficial
        res_detail = self.client.get(f"/protocol/settlement/{settlement.pk}/")
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "Protocolo de Cooperação Desportiva")
        self.assertContains(res_detail, "Pela Associação Cultural e Recreativa (ACR)")
        self.assertContains(res_detail, "Pelo Ginásio Proform SC")

        # 4. Avançar estado do fecho (draft -> approved -> settled)
        res_toggle1 = self.client.post(f"/protocol/settlement/{settlement.pk}/toggle-status/", follow=True)
        self.assertEqual(res_toggle1.status_code, 200)
        settlement.refresh_from_db()
        self.assertEqual(settlement.status, ProtocolPeriodSettlement.Status.APPROVED)

        res_toggle2 = self.client.post(f"/protocol/settlement/{settlement.pk}/toggle-status/", follow=True)
        self.assertEqual(res_toggle2.status_code, 200)
        settlement.refresh_from_db()
        self.assertEqual(settlement.status, ProtocolPeriodSettlement.Status.SETTLED)
        self.assertIsNotNone(settlement.settled_at)

    def test_instructor_commission_toggle_paid(self):
        """Valida a marcação e liquidação individual de comissões de instrutor."""
        comm = InstructorCommission.objects.create(
            organization=self.org,
            instructor=self.inst_carlos,
            event=self.event_jj,
            total_revenue=Decimal("100.00"),
            commission_rate=Decimal("60.00"),
            is_paid=False
        )
        self.assertFalse(comm.is_paid)

        # POST para toggle-paid
        res = self.client.post(f"/protocol/commissions/{comm.pk}/toggle-paid/", follow=True)
        self.assertEqual(res.status_code, 200)
        comm.refresh_from_db()
        self.assertTrue(comm.is_paid)
        self.assertIsNotNone(comm.payment_date)

        # Desmarcar pagamento
        res2 = self.client.post(f"/protocol/commissions/{comm.pk}/toggle-paid/", follow=True)
        self.assertEqual(res2.status_code, 200)
        comm.refresh_from_db()
        self.assertFalse(comm.is_paid)
        self.assertIsNone(comm.payment_date)


class DynamicProtocolConfigurationTestCase(TestCase):
    """
    Testes de cobertura abrangentes para a parametrização 100% dinâmica do protocolo:
    - Seguradoras, mediadores, contactos e apólices dinâmicas
    - Diretores técnicos e projetos IPDJ alternáveis
    - Espaços e regimes de cedência municipal vs arrendamento
    - Fichas de atletas com sócio vs não sócio, parentesco de emergência e consentimentos legais
    - Impacto dinâmico no cálculo das quotas e apuramentos mensais do protocolo
    """
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="acr.local",
            org_type=Organization.Type.BOTH
        )
        self.user = User.objects.create_superuser(
            username="admin_dynamic",
            email="admin_dynamic@test.local",
            password="testpassword123"
        )
        self.client.login(username="admin_dynamic", password="testpassword123")

        self.director_daniel = Instructor.objects.create(
            organization=self.org,
            first_name="Daniel",
            last_name="Coelho",
            email="daniel.coelho@proform.pt",
            is_technical_director=True,
            ipdj_license_number="97575",
            ipdj_project_name="Protocolo Artes Marciais ACR-Proform"
        )

        self.director_novo = Instructor.objects.create(
            organization=self.org,
            first_name="Rui",
            last_name="Menezes",
            email="rui.menezes@ipdj.pt",
            is_technical_director=False,
            ipdj_license_number="105820",
            ipdj_project_name="Novo Projeto IPDJ 2026"
        )

    def test_default_config_creation(self):
        """Verifica criação automática de configuração com dados padrão ao invocar get_protocol_config."""
        config = self.org.get_protocol_config()
        self.assertIsNotNone(config)
        self.assertEqual(config.insurance_company, "Generali Seguros, S.A.")
        self.assertEqual(config.insurance_policy_number, "0010189147")
        self.assertEqual(config.acr_admin_fee_per_athlete, Decimal("1.00"))
        self.assertEqual(config.insurance_annual_premium, Decimal("362.82"))

    def test_settings_view_post_updates_configuration(self):
        """Valida que o POST na view de definições atualiza dinamicamente seguradora, mediador e projeto IPDJ."""
        config = self.org.get_protocol_config()
        data = {
            # Tab 1: Entidades
            "acr_official_name": "ACR de Basto",
            "acr_nipc": "510695744",
            "acr_address": "Lugar da Igreja, Basto",
            "acr_representative_name": "Paulo Sérgio",
            "acr_representative_role": "Presidente",
            "proform_official_name": "Proform SC",
            "proform_nipc": "210263601",
            "proform_address": "Rua Senhora da Conceição 24",
            "proform_representative_name": "Daniel Coelho",
            "proform_representative_role": "Diretor Técnico",
            # Tab 2: Seguradora & Mediador
            "insurance_company": "Fidelidade - Companhia de Seguros, S.A.",
            "insurance_policy_number": "9988776655",
            "insurance_product_name": "Seguro Desportivo Fidelidade",
            "insurance_annual_premium": "420.00",
            "insurance_base_insured_count": 25,
            "insurance_claim_deadline_days": 3,
            "capital_death_disability": "35000.00",
            "capital_treatment": "6000.00",
            "treatment_deductible": "50.00",
            "capital_funeral": "3500.00",
            "broker_name": "Novo Mediador Seguros Lda",
            "broker_asf_number": "987654321",
            "broker_phone": "+351 919 999 888",
            "broker_address": "Celorico de Basto",
            # Tab 3: Direção Técnica & IPDJ
            "active_technical_director": self.director_novo.pk,
            "active_ipdj_project": "Candidatura IPDJ - Artes Marciais Inclusivas 2026",
            # Tab 5: Regras Financeiras
            "acr_admin_fee_per_athlete": "2.00",
            "insurance_split_mode": ProtocolConfiguration.InsuranceSplitMode.ANNUAL_DONATION,
        }

        response = self.client.post("/settings/", data, follow=True)
        self.assertEqual(response.status_code, 200)

        config.refresh_from_db()
        self.assertEqual(config.insurance_company, "Fidelidade - Companhia de Seguros, S.A.")
        self.assertEqual(config.insurance_policy_number, "9988776655")
        self.assertEqual(config.insurance_annual_premium, Decimal("420.00"))
        self.assertEqual(config.broker_name, "Novo Mediador Seguros Lda")
        self.assertEqual(config.active_technical_director, self.director_novo)
        self.assertEqual(config.active_ipdj_project, "Candidatura IPDJ - Artes Marciais Inclusivas 2026")
        self.assertEqual(config.acr_admin_fee_per_athlete, Decimal("2.00"))

    def test_athlete_creation_with_member_category_and_consents(self):
        """Valida que atletas podem ser criados com categoria associativa (Sócio vs Não Sócio) e consentimentos legais."""
        person = Person.objects.create(
            organization=self.org,
            first_name="Diogo",
            last_name="Fernandes",
            email="diogo.fernandes@example.local",
            member_category=Person.MemberCategory.SOCIO,
            emergency_contact="Maria Fernandes 912345678",
            emergency_relationship="Mãe",
            consent_rgpd=True,
            image_consent=True,
            regulation_accepted=True,
            status=Person.Status.ACTIVE
        )
        self.assertEqual(person.member_category, Person.MemberCategory.SOCIO)
        self.assertEqual(person.emergency_relationship, "Mãe")
        self.assertTrue(person.consent_rgpd)
        self.assertTrue(person.image_consent)
        self.assertTrue(person.regulation_accepted)

        # Verificar renderização na ficha de detalhe
        res = self.client.get(f"/clients/{person.pk}/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Sócio ACR")
        self.assertContains(res, "Maria Fernandes 912345678")
        self.assertContains(res, "Mãe")
        self.assertContains(res, "Autorizado")
        self.assertContains(res, "Aceite")

    def test_resource_facility_type_and_cession(self):
        """Valida o registo de espaços com regime de cedência municipal ou arrendamento."""
        pavilhao = Resource.objects.create(
            organization=self.org,
            name="Pavilhão da Antiga C+S",
            facility_type=Resource.FacilityType.MUNICIPAL_CESSION,
            cession_entity="Município de Celorico de Basto",
            address="C+S Celorico de Basto",
            capacity=30
        )
        self.assertEqual(pavilhao.facility_type, Resource.FacilityType.MUNICIPAL_CESSION)
        self.assertEqual(pavilhao.cession_entity, "Município de Celorico de Basto")

        res_list = self.client.get("/resources/")
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, "Pavilhão da Antiga C+S")
        self.assertContains(res_list, "Cedência Mun.")

    def test_calculate_period_protocol_split_with_dynamic_rules(self):
        """Valida que o apuramento financeiro reflete dinamicamente a parametrização atual."""
        from core.services.protocol_finance import calculate_period_protocol_split

        config = self.org.get_protocol_config()
        config.acr_admin_fee_per_athlete = Decimal("2.50")
        config.insurance_annual_premium = Decimal("480.00")
        config.save()

        # Criar 10 atletas ativos
        for i in range(10):
            Person.objects.create(
                organization=self.org,
                first_name=f"Atleta{i}",
                last_name="Teste",
                email=f"atleta{i}@test.local",
                status=Person.Status.ACTIVE
            )

        start = timezone.now().date()
        end = start + timedelta(days=30)

        split = calculate_period_protocol_split(self.org, start, end)

        # 10 atletas * 2.50€ = 25.00€
        self.assertEqual(split["active_athletes_count"], 10)
        self.assertEqual(split["contractual_acr_admin"], Decimal("25.00"))
        # 480.00€ / 12 = 40.00€
        self.assertEqual(split["monthly_insurance_share"], Decimal("40.00"))
        self.assertEqual(split["protocol_config"].acr_admin_fee_per_athlete, Decimal("2.50"))


class GanttModernizationTestCase(TestCase):
    """Testes automatizados para a modernização do Gantt, grelha semanal e séries recorrentes."""

    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="acr.local",
            org_type=Organization.Type.BOTH
        )
        self.user = User.objects.create_superuser("admin_gantt", "admin_gantt@acr.local", "secret123")
        self.client.force_login(self.user)

        self.pavilhao = Resource.objects.create(
            organization=self.org,
            name="Pavilhão Central",
            capacity=30,
            entity_type=Resource.EntityType.ACR
        )
        self.sala_judo = Resource.objects.create(
            organization=self.org,
            name="Sala de Judo",
            capacity=15,
            entity_type=Resource.EntityType.PROFORM
        )
        self.judo = Modality.objects.create(
            organization=self.org,
            name="Judo",
            color="#2563eb",
            entity_type=Modality.EntityType.PROFORM
        )
        self.karate = Modality.objects.create(
            organization=self.org,
            name="Karaté",
            color="#dc2626",
            entity_type=Modality.EntityType.ACR
        )
        self.instructor = Instructor.objects.create(
            organization=self.org,
            first_name="Daniel",
            last_name="Coelho",
            email="daniel.coelho@acr.local"
        )

    def test_recurring_event_series_creation_and_conflict_avoidance(self):
        """Testa criação de série recorrente e a prevenção atómica de conflitos por data."""
        from core.services.scheduling import create_recurring_event_series

        # Definir período: 2 semanas a partir de uma Segunda-feira futura
        today = timezone.now().date()
        # Encontrar a próxima segunda-feira
        days_ahead = (7 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        start_date = today + timedelta(days=days_ahead)
        end_date = start_date + timedelta(days=13)  # 2 semanas completas

        # Pré-agendar um evento conflituoso na primeira Segunda-feira na Sala de Judo
        conflict_start = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time().replace(hour=18, minute=0)))
        conflict_end = conflict_start + timedelta(hours=1, minutes=30)
        Event.objects.create(
            organization=self.org,
            resource=self.sala_judo,
            title="Evento em Conflito Pré-existente",
            starts_at=conflict_start,
            ends_at=conflict_end,
            capacity=15,
        )

        # Criar série recorrente para Segundas e Quartas (weekdays [0, 2]), 18:00 - 19:30
        result = create_recurring_event_series(
            organization=self.org,
            resource=self.sala_judo,
            start_time="18:00",
            end_time="19:30",
            start_date=start_date,
            end_date=end_date,
            weekdays=[0, 2],
            title="Treino Judo Recorrente",
            modality=self.judo,
            instructor=self.instructor,
            capacity=15,
        )

        # No período de 14 dias há 2 Segundas e 2 Quartas (4 ocorrências no total).
        # A 1ª Segunda tem conflito e deve ser ignorada; 3 ocorrências devem ser criadas com sucesso.
        self.assertEqual(result["created_count"], 3)
        self.assertEqual(result["skipped_count"], 1)
        self.assertEqual(result["skipped_dates"][0]["date"], start_date.isoformat())
        self.assertIsNotNone(result["recurrence_group_id"])

        # Verificar se todos os eventos criados partilham o mesmo recurrence_group_id
        events = Event.objects.filter(recurrence_group_id=result["recurrence_group_id"])
        self.assertEqual(events.count(), 3)
        for ev in events:
            self.assertEqual(ev.title, "Treino Judo Recorrente")
            self.assertEqual(ev.instructor, self.instructor)
            self.assertEqual(ev.resource, self.sala_judo)

    def test_gantt_data_daily_and_weekly_api(self):
        """Testa endpoint gantt_data retornando dados com ocupação e suporte a vista semanal."""
        # Criar evento com reservas para testar occupancy_pct
        start_dt = timezone.now() + timedelta(days=1)
        end_dt = start_dt + timedelta(hours=1)
        ev = Event.objects.create(
            organization=self.org,
            resource=self.pavilhao,
            modality=self.karate,
            instructor=self.instructor,
            title="Karaté Adultos",
            starts_at=start_dt,
            ends_at=end_dt,
            capacity=20
        )
        athlete = Person.objects.create(organization=self.org, first_name="Atleta", last_name="1")
        Booking.objects.create(
            organization=self.org,
            event=ev,
            person=athlete,
            status=Booking.Status.CONFIRMED
        )

        # 1. Testar vista diária
        res_day = self.client.get(f"/gantt/data/?date={start_dt.date().isoformat()}&view_type=day")
        self.assertEqual(res_day.status_code, 200)
        data_day = res_day.json()
        self.assertEqual(data_day["view_type"], "day")
        self.assertTrue(len(data_day["events"]) >= 1)
        found_ev = next(e for e in data_day["events"] if e["id"] == ev.id)
        self.assertEqual(found_ev["bookings_count"], 1)
        self.assertEqual(found_ev["capacity"], 20)
        self.assertEqual(found_ev["occupancy_pct"], 5.0)
        self.assertIn("/events/", found_ev["checkin_url"])
        self.assertIn("/checkin/", found_ev["checkin_url"])

        # 2. Testar vista semanal
        res_week = self.client.get(f"/gantt/data/?date={start_dt.date().isoformat()}&view_type=week")
        self.assertEqual(res_week.status_code, 200)
        data_week = res_week.json()
        self.assertEqual(data_week["view_type"], "week")
        self.assertIn("week_start", data_week)
        self.assertIn("week_end", data_week)

        # 3. Testar filtros (filtro de recurso inexistente retorna vazio)
        res_filtered = self.client.get(f"/gantt/data/?date={start_dt.date().isoformat()}&resource_id={self.sala_judo.id}")
        self.assertEqual(res_filtered.status_code, 200)
        data_filtered = res_filtered.json()
        self.assertEqual(len(data_filtered["events"]), 0)

    def test_create_event_from_gantt_endpoint_with_recurrence(self):
        """Testa o endpoint POST /gantt/create-event/ para criação de série recorrente."""
        today = timezone.now().date()
        rec_end = today + timedelta(days=21)

        payload = {
            "resource_id": self.sala_judo.id,
            "date": today.isoformat(),
            "start_time": "10:00",
            "end_time": "11:00",
            "title": "Aulas Judo Recorrentes API",
            "event_type": "open_class",
            "modality_id": self.judo.id,
            "instructor_id": self.instructor.id,
            "capacity": 12,
            "is_recurring": True,
            "recurrence_end_date": rec_end.isoformat(),
            "recurrence_weekdays": [today.weekday()]  # apenas o dia da semana atual
        }

        res = self.client.post(
            "/gantt/create-event/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["is_recurring"])
        self.assertGreater(data["created_count"], 0)
        self.assertIsNotNone(data["recurrence_group_id"])

        # Testar eliminação de toda a série
        event_id = data["event_id"]
        del_res = self.client.post(
            "/gantt/delete-event/",
            data=json.dumps({"event_id": event_id, "delete_series": True}),
            content_type="application/json"
        )
        self.assertEqual(del_res.status_code, 200)
        del_data = del_res.json()
        self.assertTrue(del_data["success"])
        self.assertTrue(del_data["series_deleted"])

        # Confirmar que todos os eventos da série foram removidos
        remaining = Event.objects.filter(recurrence_group_id=data["recurrence_group_id"]).count()
        self.assertEqual(remaining, 0)

    def test_gantt_system_redirects_to_unified_gantt(self):
        """Testa o redirecionamento de compatibilidade de /gantt-system/ para /gantt/."""
        res = self.client.get("/gantt-system/")
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, "/gantt/")


class AssociationAndKioskTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="testserver",
            org_type=Organization.Type.BOTH
        )
        self.user = User.objects.create_user(username="admin_test", password="password", is_superuser=True)
        self.client.login(username="admin_test", password="password")

        # Configuração do Protocolo
        self.config = ProtocolConfiguration.objects.create(
            organization=self.org,
            acr_official_name="ACR - Associação Cultural e Recreativa de Basto",
            acr_nipc="510695744",
            insurance_company="Generali Seguros, S.A.",
            insurance_policy_number="0010189147",
            insurance_policy_start=timezone.now().date() - timedelta(days=30),
            insurance_policy_expiry=timezone.now().date() + timedelta(days=335),
            insurance_annual_premium=Decimal("362.82"),
        )

        self.pavilhao = Resource.objects.create(
            organization=self.org,
            name="Pavilhão da Antiga C+S",
            capacity=25,
            facility_type=Resource.FacilityType.MUNICIPAL_CESSION,
        )

        self.judo = Modality.objects.create(
            organization=self.org,
            name="Judo",
            entity_type=Modality.EntityType.BOTH,
            default_duration_minutes=60,
        )

        self.instructor = Instructor.objects.create(
            organization=self.org,
            first_name="Paulo",
            last_name="Teixeira",
            email="paulo.teixeira@acr.pt",
            is_active=True,
        )

    def test_automatic_sequential_member_numbering(self):
        """Verifica se sócios recebem número sequencial automático da ACR e não-sócios não."""
        s1 = Person.objects.create(
            organization=self.org,
            first_name="Mariana",
            last_name="Silva",
            member_category=Person.MemberCategory.SOCIO,
        )
        self.assertEqual(s1.member_number, 1)

        s2 = Person.objects.create(
            organization=self.org,
            first_name="Leonardo",
            last_name="Alves",
            member_category=Person.MemberCategory.SOCIO,
        )
        self.assertEqual(s2.member_number, 2)

        ns = Person.objects.create(
            organization=self.org,
            first_name="Carlos",
            last_name="Visitante",
            member_category=Person.MemberCategory.NAO_SOCIO,
        )
        self.assertIsNone(ns.member_number)

        # Número manual pré-atribuído deve ser preservado
        s_manual = Person.objects.create(
            organization=self.org,
            first_name="António",
            last_name="Fundador",
            member_category=Person.MemberCategory.SOCIO,
            member_number=50,
        )
        self.assertEqual(s_manual.member_number, 50)

        # Próximo deve ser 51
        s3 = Person.objects.create(
            organization=self.org,
            first_name="Tiago",
            last_name="Novo",
            member_category=Person.MemberCategory.SOCIO,
        )
        self.assertEqual(s3.member_number, 51)

    def test_qr_code_token_and_resolution(self):
        """Verifica a geração do token QR e resolução por ACR:<org>:<id>:<token>, NIF e Sócio."""
        atleta = Person.objects.create(
            organization=self.org,
            first_name="Mariana",
            last_name="Silva",
            nif="250123456",
            member_category=Person.MemberCategory.SOCIO,
            phone="912345678",
        )
        self.assertIsNotNone(atleta.qr_code_token)

        # Resolução por payload oficial ACR
        payload = f"ACR:{self.org.id}:{atleta.id}:{atleta.qr_code_token}"
        resolved = resolve_person(self.org, payload)
        self.assertEqual(resolved, atleta)

        # Resolução por NIF
        self.assertEqual(resolve_person(self.org, "250123456"), atleta)

        # Resolução por Número de Sócio (#1 ou 1)
        self.assertEqual(resolve_person(self.org, str(atleta.member_number)), atleta)
        self.assertEqual(resolve_person(self.org, f"#{atleta.member_number}"), atleta)

        # Resolução por Telefone
        self.assertEqual(resolve_person(self.org, "912345678"), atleta)

    def test_kiosk_checkin_with_valid_insurance(self):
        """Verifica check-in no quiosque com semáforo verde para atleta com apólice e exame válidos."""
        now = timezone.now()
        event = Event.objects.create(
            organization=self.org,
            resource=self.pavilhao,
            modality=self.judo,
            instructor=self.instructor,
            title="Treino de Judo",
            starts_at=now - timedelta(minutes=10),
            ends_at=now + timedelta(minutes=50),
            capacity=20,
        )

        atleta = Person.objects.create(
            organization=self.org,
            first_name="João",
            last_name="Santos",
            member_category=Person.MemberCategory.SOCIO,
            insurance_policy="0010189147",
            insurance_expiry=now.date() + timedelta(days=120),
            medical_certificate_expiry=now.date() + timedelta(days=180),
            membership_fee_status=Person.MembershipFeeStatus.UP_TO_DATE,
        )

        result = process_kiosk_checkin(self.org, f"ACR:{self.org.id}:{atleta.id}:{atleta.qr_code_token}")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "green")
        self.assertTrue(result["checked_in"])
        self.assertIsNotNone(result["event"])
        self.assertEqual(result["event"]["id"], event.id)

        # Confirma registo da presença
        booking = Booking.objects.filter(person=atleta, event=event).first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.status, Booking.Status.CHECKED_IN)

    def test_kiosk_checkin_blocks_expired_insurance(self):
        """Verifica semáforo vermelho e bloqueio se o seguro estiver expirado."""
        now = timezone.now()
        atleta = Person.objects.create(
            organization=self.org,
            first_name="Inês",
            last_name="Ferreira",
            member_category=Person.MemberCategory.SOCIO,
            insurance_policy="0010189147",
            insurance_expiry=now.date() - timedelta(days=5),  # Vencido!
            medical_certificate_expiry=now.date() + timedelta(days=90),
        )

        result = process_kiosk_checkin(self.org, str(atleta.member_number))
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "red")
        self.assertFalse(result["checked_in"])
        self.assertIn("Seguro desportivo vencido", result["blocking_reasons"][0])

    def test_athlete_graduation_and_belt_sync(self):
        """Verifica registo de graduação, sincronização do cinto e cálculo de treinos cumpridos."""
        now = timezone.now()
        event = Event.objects.create(
            organization=self.org,
            resource=self.pavilhao,
            modality=self.judo,
            instructor=self.instructor,
            title="Judo Treino 1",
            starts_at=now - timedelta(days=2),
            ends_at=now - timedelta(days=2, hours=-1),
            capacity=10,
        )

        atleta = Person.objects.create(
            organization=self.org,
            first_name="Rui",
            last_name="Costa",
            member_category=Person.MemberCategory.SOCIO,
            current_belt="Cinto Branco",
        )

        # Registar 1 treino concluído
        Booking.objects.create(
            organization=self.org,
            person=atleta,
            event=event,
            status=Booking.Status.CHECKED_IN,
        )

        # Submeter nova graduação via endpoint
        res = self.client.post(f"/clients/{atleta.pk}/graduation/add/", data={
            "modality": self.judo.id,
            "rank_name": "Cinto Amarelo (7º Kyu)",
            "rank_order": "2",
            "awarded_date": now.date().isoformat(),
            "examiner": self.instructor.id,
            "certificate_number": "CERT-2024-001",
        })
        self.assertEqual(res.status_code, 302)

        # Verifica sincronização
        atleta.refresh_from_db()
        self.assertEqual(atleta.current_belt, "Cinto Amarelo (7º Kyu)")

        grad = AthleteGraduation.objects.filter(person=atleta).first()
        self.assertIsNotNone(grad)
        self.assertEqual(grad.rank_name, "Cinto Amarelo (7º Kyu)")
        self.assertEqual(grad.classes_attended_count, 1)  # Contabilizou 1 aula

    def test_association_governance_and_card_views(self):
        """Verifica rendering das páginas de Governança da ACR e Cartão Digital."""
        # Criar órgãos sociais
        board = GoverningBody.objects.create(
            organization=self.org,
            body_type=GoverningBody.BodyType.BOARD,
            term_label="2024–2028",
            start_date=timezone.now().date() - timedelta(days=100),
            end_date=timezone.now().date() + timedelta(days=1000),
            is_active=True,
        )
        GoverningBodyMember.objects.create(
            governing_body=board,
            name="Paulo Teixeira",
            role="Presidente da Direção",
            order=1,
        )

        atleta = Person.objects.create(
            organization=self.org,
            first_name="Mariana",
            last_name="Silva",
            member_category=Person.MemberCategory.SOCIO,
            nif="250999888",
        )

        # 1. Página de Governança
        res_gov = self.client.get("/association/governance/")
        self.assertEqual(res_gov.status_code, 200)
        self.assertContains(res_gov, "Órgãos Sociais")
        self.assertContains(res_gov, "Paulo Teixeira")

        # 2. Cartão Digital do Sócio
        res_card = self.client.get(f"/clients/{atleta.pk}/card/")
        self.assertEqual(res_card.status_code, 200)
        self.assertContains(res_card, "Cartão Digital")
        self.assertContains(res_card, "0010189147")  # Apólice Generali
        self.assertContains(res_card, "Mariana Silva")

        # 3. Quiosque do Pavilhão
        res_kiosk = self.client.get("/kiosk/")
        self.assertEqual(res_kiosk.status_code, 200)
        self.assertContains(res_kiosk, "ACR DE BASTO")


# ==============================================================================
# E2E TRACK: TIER 1 - FUNCTIONAL AND PERMISSION TESTS (R1)
# ==============================================================================

@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class Tier1FunctionalAndPermissionsTestCase(TestCase):
    """
    Tier 1: Functional and Permission tests.
    Audita restrições de papéis de utilizador (@role_required) e integridade
    de rendering dos dashboards operacionais e de relatórios.
    """
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="testserver",
            org_type=Organization.Type.BOTH
        )
        self.admin_user = User.objects.create_superuser(
            username="admin_tier1",
            password="password123",
            email="admin1@test.com"
        )
        UserProfile.objects.create(
            user=self.admin_user,
            organization=self.org,
            user_type=UserProfile.UserType.ADMIN
        )

        self.client_user = User.objects.create_user(
            username="client_tier1",
            password="password123",
            email="client1@test.com"
        )
        self.client_person = Person.objects.create(
            organization=self.org,
            first_name="Atleta",
            last_name="Teste",
            email="client1@test.com"
        )
        UserProfile.objects.create(
            user=self.client_user,
            organization=self.org,
            user_type=UserProfile.UserType.CLIENT,
            person=self.client_person
        )

        self.inst_user = User.objects.create_user(
            username="inst_tier1",
            password="password123",
            email="instructor1@test.com"
        )
        self.instructor = Instructor.objects.create(
            organization=self.org,
            first_name="Mestre",
            last_name="Instrutor",
            email="instructor1@test.com",
            is_active=True
        )
        UserProfile.objects.create(
            user=self.inst_user,
            organization=self.org,
            user_type=UserProfile.UserType.INSTRUCTOR,
            instructor=self.instructor
        )

        self.resource = Resource.objects.create(
            organization=self.org,
            name="Sala de Treino 1",
            capacity=20,
            is_available=True
        )
        self.modality = Modality.objects.create(
            organization=self.org,
            name="Judo",
            is_active=True
        )
        self.event = Event.objects.create(
            organization=self.org,
            resource=self.resource,
            modality=self.modality,
            instructor=self.instructor,
            title="Aula de Judo",
            starts_at=timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1),
            ends_at=timezone.now().replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1),
            capacity=15
        )
        self.client = Client()

    def test_unauthorized_client_role_accessing_reports_dashboard_returns_403(self):
        """Clientes comuns não autorizados acedendo a /reports/dashboard/ devem receber HTTP 403 Forbidden."""
        self.client.login(username="client_tier1", password="password123")
        response = self.client.get("/reports/dashboard/")
        self.assertEqual(response.status_code, 403, "Cliente comum não deve ter acesso ao dashboard de relatórios")

    def test_unauthorized_client_role_accessing_reports_data_summary_returns_403(self):
        """Clientes comuns não autorizados acedendo a /reports/data/summary/ devem receber HTTP 403 Forbidden."""
        self.client.login(username="client_tier1", password="password123")
        response = self.client.get("/reports/data/summary/")
        self.assertEqual(response.status_code, 403, "Cliente comum não deve ter acesso aos dados sumários de relatórios")

    def test_instructor_role_accessing_gantt_events_json_returns_200(self):
        """Instrutores devem ter autorização legítima (HTTP 200) para aceder ao feed /gantt/events-json/."""
        self.client.login(username="inst_tier1", password="password123")
        response = self.client.get("/gantt/events-json/")
        self.assertEqual(response.status_code, 200, "Instrutor deve conseguir aceder a /gantt/events-json/")

    def test_admin_dashboard_renders_without_field_error(self):
        """Dashboard administrativo (/dashboard/) deve renderizar com sucesso (HTTP 200)."""
        self.client.login(username="admin_tier1", password="password123")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_clients_overview_renders_without_field_error(self):
        """Visão geral de clientes (/dashboard/clients/) deve renderizar com sucesso (HTTP 200)."""
        self.client.login(username="admin_tier1", password="password123")
        response = self.client.get("/dashboard/clients/")
        self.assertEqual(response.status_code, 200)

    def test_instructors_overview_renders_without_field_error(self):
        """Visão geral de instrutores (/dashboard/instructors/) não pode rebentar com FieldError no Count('events')."""
        self.client.login(username="admin_tier1", password="password123")
        response = self.client.get("/dashboard/instructors/")
        self.assertEqual(response.status_code, 200, "instructors_overview não pode falhar com FieldError")


# ==============================================================================
# E2E TRACK: TIER 2 - BOUNDARY & INPUT ROBUSTNESS TESTS (R1 & R2)
# ==============================================================================

@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class Tier2BoundaryAndRobustnessTestCase(TestCase):
    """
    Tier 2: Boundary & Input Robustness tests.
    Validação contra payloads malformatados, strings em campos de ID numérico,
    colisões de unicidade e consistência de namespaces de redirecionamento.
    """
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="testserver",
            org_type=Organization.Type.BOTH
        )
        self.admin_user = User.objects.create_superuser(
            username="admin_tier2",
            password="password123",
            email="admin2@test.com"
        )
        UserProfile.objects.create(
            user=self.admin_user,
            organization=self.org,
            user_type=UserProfile.UserType.ADMIN
        )
        self.client = Client()
        self.client.login(username="admin_tier2", password="password123")

        self.resource = Resource.objects.create(
            organization=self.org,
            name="Dojo Principal",
            capacity=15,
            is_available=True
        )
        self.instructor = Instructor.objects.create(
            organization=self.org,
            first_name="Manel",
            last_name="Silva",
            email="manel@test.com",
            is_active=True
        )
        self.modality = Modality.objects.create(
            organization=self.org,
            name="Karaté",
            is_active=True
        )
        self.person = Person.objects.create(
            organization=self.org,
            first_name="Carlos",
            last_name="Atleta",
            email="carlos@test.com"
        )
        self.now = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        self.start = self.now + timedelta(days=2)
        self.end = self.start + timedelta(hours=1)
        self.event = Event.objects.create(
            organization=self.org,
            resource=self.resource,
            instructor=self.instructor,
            modality=self.modality,
            title="Aula de Karaté",
            starts_at=self.start,
            ends_at=self.end,
            capacity=10
        )

    def test_gantt_create_event_malformed_input_returns_400_not_500(self):
        """Criação via Gantt com valores não-numéricos ou mal formatados devolve 400 ou 404, nunca HTTP 500."""
        payload = {
            "resource_id": "not_an_id",
            "instructor_id": "not_an_id",
            "date": "2026-09-10",
            "start_time": "10:00",
            "end_time": "11:00",
            "capacity": "not_a_number"
        }
        res = self.client.post("/gantt/create-event/", json.dumps(payload), content_type="application/json")
        self.assertNotEqual(res.status_code, 500, "Criação com IDs/capacidade inválidos não deve gerar 500")
        self.assertIn(res.status_code, [400, 404])

        payload_recur = {
            "resource_id": self.resource.id,
            "instructor_id": self.instructor.id,
            "date": "2026-09-10",
            "start_time": "10:00",
            "end_time": "11:00",
            "is_recurring": True,
            "recurrence_end_date": "2026-09-30",
            "recurrence_weekdays": ["segunda", "terca"]
        }
        res2 = self.client.post("/gantt/create-event/", json.dumps(payload_recur), content_type="application/json")
        self.assertNotEqual(res2.status_code, 500, "Série recorrente com weekdays inválidos não deve gerar 500")
        self.assertIn(res2.status_code, [400, 404])

    def test_gantt_update_event_malformed_input_returns_400_or_404_not_500(self):
        """Atualização via Gantt com ID não numérico ou capacidade inválida não deve gerar HTTP 500."""
        payload = {
            "event_id": "invalid_event_id",
            "capacity": "non_integer"
        }
        res = self.client.post("/gantt/update-event/", json.dumps(payload), content_type="application/json")
        self.assertNotEqual(res.status_code, 500)
        self.assertIn(res.status_code, [400, 404])

    def test_gantt_delete_event_malformed_id_returns_400_or_404_not_500(self):
        """Eliminação via API do Gantt com event_id inválido devolve erro controlado, nunca 500."""
        payload = {"event_id": "abc_xyz"}
        res = self.client.post("/gantt/delete-event/", json.dumps(payload), content_type="application/json")
        self.assertNotEqual(res.status_code, 500)
        self.assertIn(res.status_code, [400, 404])

    def test_validate_conflict_api_malformed_id_returns_400_not_500(self):
        """Validação de conflitos com IDs de recurso/instrutor inválidos devolve 400, nunca 500."""
        payload = {
            "resource_id": "abc",
            "instructor_id": "xyz",
            "starts_at": "2026-09-10T10:00:00",
            "ends_at": "2026-09-10T11:00:00"
        }
        res = self.client.post("/api/validate-conflict/", json.dumps(payload), content_type="application/json")
        self.assertNotEqual(res.status_code, 500)
        self.assertIn(res.status_code, [400, 404])

    def test_event_quick_add_attendance_malformed_person_id_returns_400_or_404_not_500(self):
        """Check-in rápido com person_id alfanumérico não tratado devolve erro controlado, nunca 500."""
        res = self.client.post(f"/events/{self.event.id}/quick-add/", {"person_id": "not_an_int"})
        self.assertNotEqual(res.status_code, 500)
        self.assertIn(res.status_code, [400, 404])

    def test_athlete_graduation_add_malformed_modality_id_returns_400_or_404_not_500(self):
        """Adição de graduação com modalidade inválida não deve quebrar a aplicação com 500."""
        res = self.client.post(f"/clients/{self.person.id}/graduation/add/", {
            "modality": "not_a_number",
            "rank_name": "Cinto Azul"
        })
        self.assertNotEqual(res.status_code, 500)
        self.assertIn(res.status_code, [400, 404, 302])

    def test_duplicate_modality_returns_form_error_not_500(self):
        """Submissão de modalidade com nome duplicado na mesma organização devolve erro no form (200), não IntegrityError 500."""
        Modality.objects.create(organization=self.org, name="Judo", entity_type="acr")
        res = self.client.post("/modalities/add/", {
            "name": "Judo",
            "entity_type": "acr",
            "max_capacity": 15
        })
        self.assertNotEqual(res.status_code, 500, "Submissão de modalidade duplicada não deve gerar IntegrityError 500")
        self.assertEqual(res.status_code, 200)

    def test_duplicate_resource_returns_form_error_not_500(self):
        """Submissão de recurso com nome duplicado na mesma organização devolve erro no form (200), não IntegrityError 500."""
        Resource.objects.create(organization=self.org, name="Estúdio Yoga", capacity=10)
        res = self.client.post("/resources/add/", {
            "name": "Estúdio Yoga",
            "capacity": 10,
            "entity_type": "acr"
        })
        self.assertNotEqual(res.status_code, 500, "Submissão de recurso duplicado não deve gerar IntegrityError 500")
        self.assertEqual(res.status_code, 200)

    def test_payment_create_with_none_plan_fields_does_not_raise_type_error(self):
        """Criação de pagamento com plano tendo credits_validity_days ou duration_months como None não causa TypeError."""
        plan = PaymentPlan.objects.create(
            organization=self.org,
            name="Pack Avulso Sem Validade",
            plan_type=PaymentPlan.PlanType.CREDITS,
            credits_included=5,
            credits_validity_days=30,
            price=Decimal("40.00")
        )
        with unittest.mock.patch.object(PaymentPlan, 'credits_validity_days', None):
            res = self.client.post("/payments/add/", {
                "person": self.person.id,
                "payment_plan": plan.id,
                "amount": "40.00",
                "method": "cash",
                "paid_date": timezone.now().date().isoformat(),
                "auto_activate": "on"
            })
            self.assertNotEqual(res.status_code, 500, "payment_create não deve lançar TypeError com credits_validity_days=None")

    def test_client_subscribe_with_none_plan_fields_does_not_raise_type_error(self):
        """Subscrição direta de cliente em plano com valores de duração None não causa TypeError."""
        plan = PaymentPlan.objects.create(
            organization=self.org,
            name="Mensalidade Sem Duracao Fixa",
            plan_type=PaymentPlan.PlanType.MONTHLY,
            duration_months=1,
            price=Decimal("35.00")
        )
        with unittest.mock.patch.object(PaymentPlan, 'duration_months', None):
            res = self.client.post(f"/clients/{self.person.id}/subscribe/", {
                "payment_plan": plan.id,
                "start_date": timezone.now().date().isoformat(),
                "status": ClientSubscription.Status.ACTIVE
            })
            self.assertNotEqual(res.status_code, 500, "client_subscribe não deve lançar TypeError com duration_months=None")

    def test_redirects_resolve_correctly_with_namespace(self):
        """Garante que redirects em event_edit, event_create, instructor_edit e modality_edit usam namespace core:."""
        # 1. event_edit POST redirect
        edit_data = {
            "title": "Karaté Editado",
            "event_type": Event.EventType.OPEN_CLASS,
            "resource": self.resource.id,
            "instructor": self.instructor.id,
            "modality": self.modality.id,
            "starts_at": (self.start + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "ends_at": (self.end + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "capacity": 10
        }
        res_event = self.client.post(f"/events/{self.event.id}/edit/", edit_data)
        self.assertNotEqual(res_event.status_code, 500, "event_edit não pode rebentar com NoReverseMatch")
        self.assertEqual(res_event.status_code, 302)

        # 2. instructor_edit POST redirect
        inst_data = {
            "first_name": "Manel",
            "last_name": "Silva Editado",
            "email": "manel_edit@test.com",
            "is_active": True,
            "entity_affiliation": "acr_only"
        }
        res_inst = self.client.post(f"/instructors/{self.instructor.id}/edit/", inst_data)
        self.assertNotEqual(res_inst.status_code, 500, "instructor_edit não pode rebentar com NoReverseMatch")
        self.assertEqual(res_inst.status_code, 302)

        # 3. event_create POST redirect
        create_data = {
            "title": "Aula Nova Via Create",
            "event_type": Event.EventType.OPEN_CLASS,
            "resource": self.resource.id,
            "starts_at": (self.start + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "ends_at": (self.end + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "capacity": 10
        }
        res_create = self.client.post("/events/create/", create_data)
        self.assertNotEqual(res_create.status_code, 500, "event_create não pode rebentar com NoReverseMatch")
        self.assertEqual(res_create.status_code, 302)

        # 4. modality_add POST redirect
        mod_data = {
            "name": "Boxe Olímpico",
            "entity_type": "acr",
            "default_duration_minutes": 60,
            "max_capacity": 15
        }
        res_mod = self.client.post("/modalities/add/", mod_data)
        self.assertNotEqual(res_mod.status_code, 500, "modality_add não pode rebentar com NoReverseMatch")
        self.assertEqual(res_mod.status_code, 302)

        # 5. credit_history fallback redirect
        res_credit = self.client.get("/credit-history/?client=999999")
        self.assertNotEqual(res_credit.status_code, 500, "credit_history não pode rebentar com NoReverseMatch em core:dashboard")


# ==============================================================================
# E2E TRACK: TIER 3 - SCHEDULING & CONFLICT EDGE CASES (R2)
# ==============================================================================

@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class Tier3SchedulingAndConflictTestCase(TestCase):
    """
    Tier 3: Scheduling & Conflict Edge Cases.
    Verifica limites físicos de espaço, sobreposições de recursos e instrutores,
    lotação ativa com presenças, lista de espera e reembolso de créditos.
    """
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="testserver",
            org_type=Organization.Type.BOTH
        )
        self.admin_user = User.objects.create_superuser(
            username="admin_tier3",
            password="password123",
            email="admin3@test.com"
        )
        UserProfile.objects.create(
            user=self.admin_user,
            organization=self.org,
            user_type=UserProfile.UserType.ADMIN
        )
        self.client = Client()
        self.client.login(username="admin_tier3", password="password123")

        self.sala1 = Resource.objects.create(organization=self.org, name="Sala Tatami 1", capacity=10, is_available=True)
        self.sala2 = Resource.objects.create(organization=self.org, name="Sala Tatami 2", capacity=8, is_available=True)
        self.instructor = Instructor.objects.create(
            organization=self.org,
            first_name="Pedro",
            last_name="Alves",
            email="pedro@test.com",
            is_active=True
        )
        self.modality = Modality.objects.create(organization=self.org, name="Judo", is_active=True)

        self.ath1 = Person.objects.create(organization=self.org, first_name="Atleta1", last_name="Teste", email="ath1@test.com")
        self.ath2 = Person.objects.create(organization=self.org, first_name="Atleta2", last_name="Teste", email="ath2@test.com")
        self.ath3 = Person.objects.create(organization=self.org, first_name="Atleta3", last_name="Teste", email="ath3@test.com")

        self.base_start = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=5)
        self.base_end = self.base_start + timedelta(hours=1)

    def test_room_overlap_in_event_add_returns_form_error_not_500(self):
        """Conflito de sala na submissão web tradicional (/events/add/) deve devolver erro de formulário, nunca HTTP 500."""
        Event.objects.create(
            organization=self.org,
            resource=self.sala1,
            instructor=self.instructor,
            title="Aula Base Sala 1",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=10
        )
        post_data = {
            "title": "Aula Conflito Sala",
            "event_type": Event.EventType.OPEN_CLASS,
            "resource": self.sala1.id,
            "instructor": self.instructor.id,
            "starts_at": (self.base_start + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            "ends_at": (self.base_end + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            "capacity": 10
        }
        res = self.client.post("/events/add/", post_data)
        self.assertNotEqual(res.status_code, 500, "Conflito de sala em event_add não pode resultar em 500 ValidationError")
        self.assertEqual(res.status_code, 200)

    def test_room_overlap_in_event_create_returns_form_error_not_500(self):
        """Conflito de sala em /events/create/ deve devolver erro no formulário, nunca HTTP 500."""
        Event.objects.create(
            organization=self.org,
            resource=self.sala1,
            title="Aula Prévia",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=10
        )
        post_data = {
            "title": "Aula Nova Conflituosa",
            "event_type": Event.EventType.OPEN_CLASS,
            "resource": self.sala1.id,
            "starts_at": (self.base_start + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
            "ends_at": (self.base_end + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
            "capacity": 8
        }
        res = self.client.post("/events/create/", post_data)
        self.assertNotEqual(res.status_code, 500, "Conflito em event_create não pode gerar 500")
        self.assertEqual(res.status_code, 200)

    def test_instructor_overlap_across_different_rooms_returns_form_error_not_500(self):
        """Mesmo instrutor agendado simultaneamente em salas distintas deve gerar erro no form, nunca 500."""
        Event.objects.create(
            organization=self.org,
            resource=self.sala1,
            instructor=self.instructor,
            title="Aula Instrutor Sala 1",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=10
        )
        post_data = {
            "title": "Aula Instrutor Sala 2",
            "event_type": Event.EventType.OPEN_CLASS,
            "resource": self.sala2.id,
            "instructor": self.instructor.id,
            "starts_at": (self.base_start + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            "ends_at": (self.base_end + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            "capacity": 8
        }
        res = self.client.post("/events/add/", post_data)
        self.assertNotEqual(res.status_code, 500, "Conflito de instrutor não pode resultar em 500")
        self.assertEqual(res.status_code, 200)

    def test_event_capacity_cannot_exceed_resource_capacity(self):
        """Capacidade configurada para o evento não pode exceder a capacidade física da sala associada."""
        event = Event(
            organization=self.org,
            resource=self.sala1,
            title="Aula com Excesso de Capacidade",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=25
        )
        with self.assertRaises(ValidationError) as cm:
            event.full_clean()
        self.assertIn("capacidade", str(cm.exception).lower())

    def test_inactive_instructor_blocked_from_scheduling(self):
        """Instrutores com is_active=False não podem ser atribuídos a novas aulas."""
        inactive_inst = Instructor.objects.create(
            organization=self.org,
            first_name="Inativo",
            last_name="Instrutor",
            email="inativo@test.com",
            is_active=False
        )
        event = Event(
            organization=self.org,
            resource=self.sala1,
            instructor=inactive_inst,
            title="Aula com Instrutor Inativo",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=5
        )
        with self.assertRaises(ValidationError) as cm:
            event.full_clean()
        self.assertIn("inativo", str(cm.exception).lower())

    def test_unavailable_resource_blocked_from_scheduling(self):
        """Salas/recursos com is_available=False não podem acolher novos agendamentos."""
        unavail_room = Resource.objects.create(
            organization=self.org,
            name="Sala em Obras",
            capacity=10,
            is_available=False
        )
        event = Event(
            organization=self.org,
            resource=unavail_room,
            title="Aula em Espaço Indisponível",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=5
        )
        with self.assertRaises(ValidationError) as cm:
            event.full_clean()
        self.assertIn("indispon", str(cm.exception).lower())

    def test_capacity_enforcement_in_booking_add(self):
        """Criação de reservas via vista tradicional (/bookings/add/) bloqueia inscrições quando a lotação atinge o limite."""
        event = Event.objects.create(
            organization=self.org,
            resource=self.sala1,
            title="Aula Lotação 1",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=1
        )
        Booking.objects.create(
            organization=self.org,
            event=event,
            person=self.ath1,
            status=Booking.Status.CONFIRMED
        )
        res = self.client.post("/bookings/add/", {
            "event": event.id,
            "person": self.ath2.id,
            "status": Booking.Status.CONFIRMED
        })
        confirmed_count = event.bookings.filter(status=Booking.Status.CONFIRMED).count()
        self.assertEqual(confirmed_count, 1, "Apenas 1 reserva confirmada deve existir para capacity=1")

    def test_capacity_leak_checked_in_bookings_consume_capacity(self):
        """Atletas com check-in realizado (status=CHECKED_IN) devem consumir lotação, impedindo novas reservas confirmadas."""
        event = Event.objects.create(
            organization=self.org,
            resource=self.sala1,
            title="Aula Checkin Lotação 1",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=1
        )
        Booking.objects.create(
            organization=self.org,
            event=event,
            person=self.ath1,
            status=Booking.Status.CHECKED_IN
        )
        new_booking = Booking(
            organization=self.org,
            event=event,
            person=self.ath2,
            status=Booking.Status.CONFIRMED
        )
        with self.assertRaises(ValidationError) as cm:
            ensure_capacity(new_booking)
        self.assertIn("sem vagas", str(cm.exception).lower())

    def test_waitlist_paradox_waitlist_allowed_when_event_is_full(self):
        """Inscrições com status WAITLIST devem ser permitidas mesmo quando a aula se encontra com lotação esgotada."""
        event = Event.objects.create(
            organization=self.org,
            resource=self.sala1,
            title="Aula Cheia",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=1
        )
        Booking.objects.create(
            organization=self.org,
            event=event,
            person=self.ath1,
            status=Booking.Status.CONFIRMED
        )
        waitlist_booking = Booking(
            organization=self.org,
            event=event,
            person=self.ath2,
            status=Booking.Status.WAITLIST
        )
        try:
            ensure_capacity(waitlist_booking)
        except ValidationError:
            self.fail("ensure_capacity não deve bloquear reservas com status WAITLIST quando a aula está cheia")

    def test_zero_capacity_event_respected_and_not_overwritten(self):
        """Configurar capacity=0 deve ser respeitado e não sobrescrito automaticamente para a capacidade da sala."""
        event = Event(
            organization=self.org,
            resource=self.sala1,
            title="Aula Fechada a Reservas",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=0
        )
        event.clean()
        self.assertEqual(event.capacity, 0, "Capacity=0 não pode ser sobrescrito pelo recurso")

    def test_booking_cancellation_refunds_credits_to_subscription(self):
        """Cancelamento regulamentar de reserva paga com créditos devolve o crédito à subscrição do atleta."""
        plan = PaymentPlan.objects.create(
            organization=self.org,
            name="Pack 10",
            plan_type=PaymentPlan.PlanType.CREDITS,
            credits_included=10,
            price=Decimal("50.00")
        )
        sub = ClientSubscription.objects.create(
            organization=self.org,
            person=self.ath1,
            payment_plan=plan,
            status=ClientSubscription.Status.ACTIVE,
            remaining_credits=5
        )
        event = Event.objects.create(
            organization=self.org,
            resource=self.sala1,
            title="Aula Crédito",
            starts_at=self.base_start,
            ends_at=self.base_end,
            capacity=10
        )
        booking = Booking.objects.create(
            organization=self.org,
            event=event,
            person=self.ath1,
            status=Booking.Status.CONFIRMED,
            subscription_used=sub,
            credits_used=1,
            is_paid=True
        )
        result = cancel_booking(booking, self.admin_user)
        self.assertTrue(result.ok)
        sub.refresh_from_db()
        self.assertEqual(sub.remaining_credits, 6, "Crédito deve ser restituído à subscrição")
        self.assertTrue(
            CreditHistory.objects.filter(
                person=self.ath1,
                action=CreditHistory.Action.REFUND
            ).exists(),
            "Deve ser registado um movimento de reembolso no CreditHistory"
        )


# ==============================================================================
# E2E TRACK: TIER 4 - MULTI-ENTITY, MIDDLEWARE & DELETION TESTS (R3)
# ==============================================================================

@override_settings(ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False)
class Tier4MultiEntityMiddlewareTestCase(TestCase):
    """
    Tier 4: Multi-Entity Integrity, Middleware & Deletion tests.
    Audita filtros multi-entidade (ACR/Proform/Both), proteções de integridade referencial,
    e robustez do middleware perante IPv6 e hosts internos.
    """
    def setUp(self):
        self.org = Organization.objects.create(
            name="ACR & Proform SC",
            domain="testserver",
            org_type=Organization.Type.BOTH
        )
        self.admin_user = User.objects.create_superuser(
            username="admin_tier4",
            password="password123",
            email="admin4@test.com"
        )
        UserProfile.objects.create(
            user=self.admin_user,
            organization=self.org,
            user_type=UserProfile.UserType.ADMIN
        )
        self.client = Client()
        self.client.login(username="admin_tier4", password="password123")

        self.sala = Resource.objects.create(organization=self.org, name="Pavilhão", capacity=30)
        self.now = timezone.now() + timedelta(days=3)
        self.event = Event.objects.create(
            organization=self.org,
            resource=self.sala,
            title="Aula Teste Deletions",
            starts_at=self.now,
            ends_at=self.now + timedelta(hours=1),
            capacity=15
        )

    def test_client_list_filtering_entity_acr_includes_both(self):
        """Filtro ?entity=acr deve retornar praticantes 'acr_only' e praticantes com dupla filiação 'both'."""
        p_acr = Person.objects.create(organization=self.org, first_name="Acr", last_name="Only", entity_affiliation=Person.EntityAffiliation.ACR_ONLY)
        p_proform = Person.objects.create(organization=self.org, first_name="Proform", last_name="Only", entity_affiliation=Person.EntityAffiliation.PROFORM_ONLY)
        p_both = Person.objects.create(organization=self.org, first_name="Both", last_name="Entities", entity_affiliation=Person.EntityAffiliation.BOTH)

        res = self.client.get("/clients/?entity=acr")
        self.assertEqual(res.status_code, 200)
        clients = list(res.context["clients"])
        self.assertIn(p_acr, clients, "Atletas acr_only devem estar presentes ao filtrar por acr")
        self.assertIn(p_both, clients, "Atletas both devem estar presentes ao filtrar por acr")
        self.assertNotIn(p_proform, clients, "Atletas proform_only não devem estar presentes ao filtrar por acr")

    def test_client_list_filtering_entity_proform_includes_both(self):
        """Filtro ?entity=proform deve retornar praticantes 'proform_only' e praticantes com dupla filiação 'both'."""
        p_acr = Person.objects.create(organization=self.org, first_name="Acr2", last_name="Only", entity_affiliation=Person.EntityAffiliation.ACR_ONLY)
        p_proform = Person.objects.create(organization=self.org, first_name="Proform2", last_name="Only", entity_affiliation=Person.EntityAffiliation.PROFORM_ONLY)
        p_both = Person.objects.create(organization=self.org, first_name="Both2", last_name="Entities", entity_affiliation=Person.EntityAffiliation.BOTH)

        res = self.client.get("/clients/?entity=proform")
        self.assertEqual(res.status_code, 200)
        clients = list(res.context["clients"])
        self.assertIn(p_proform, clients, "Atletas proform_only devem estar presentes ao filtrar por proform")
        self.assertIn(p_both, clients, "Atletas both devem estar presentes ao filtrar por proform")
        self.assertNotIn(p_acr, clients, "Atletas acr_only não devem estar presentes ao filtrar por proform")

    def test_client_list_filtering_entity_both_returns_only_both(self):
        """Filtro ?entity=both deve retornar estritamente os praticantes com dupla filiação."""
        p_acr = Person.objects.create(organization=self.org, first_name="Acr3", last_name="Only", entity_affiliation=Person.EntityAffiliation.ACR_ONLY)
        p_both = Person.objects.create(organization=self.org, first_name="Both3", last_name="Entities", entity_affiliation=Person.EntityAffiliation.BOTH)

        res = self.client.get("/clients/?entity=both")
        self.assertEqual(res.status_code, 200)
        clients = list(res.context["clients"])
        self.assertIn(p_both, clients)
        self.assertNotIn(p_acr, clients)

    def test_client_deletion_with_linked_invoices_catches_protected_error_and_redirects(self):
        """Eliminar cliente com faturas associadas (ProtectedError) redireciona com mensagem amigável sem quebrar em 500."""
        client = Person.objects.create(
            organization=self.org,
            first_name="Cliente",
            last_name="Faturado",
            email="faturado@test.com"
        )
        Invoice.objects.create(
            organization=self.org,
            person=client,
            total=Decimal("120.00"),
            status=Invoice.Status.ISSUED
        )
        res = self.client.post(f"/clients/{client.pk}/delete/")
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Person.objects.filter(pk=client.pk).exists(), "Cliente com faturas não pode ser eliminado")
        messages = list(get_messages(res.wsgi_request))
        self.assertTrue(any("fatura" in m.message.lower() for m in messages), "Deve exibir mensagem informativa sobre faturas")

    def test_event_deletion_handles_errors_cleanly_without_500(self):
        """Eliminação de eventos trata erros de persistência/integridade devolvendo respostas controladas (não 500)."""
        with unittest.mock.patch("core.models.Event.delete", side_effect=ProtectedError("Protected relation", [self.event])):
            res_api = self.client.post(
                "/gantt/delete-event/",
                json.dumps({"event_id": self.event.id}),
                content_type="application/json"
            )
            self.assertNotEqual(res_api.status_code, 500, "delete_event_api não deve retornar status 500 sob erro de eliminação")
            self.assertIn(res_api.status_code, [400, 409])

            res_web = self.client.post(f"/events/{self.event.id}/delete/")
            self.assertNotEqual(res_web.status_code, 500, "event_delete não pode lançar 500 sob ProtectedError")
            self.assertIn(res_web.status_code, [200, 302])

    def test_middleware_database_error_defined_and_caught_without_name_error(self):
        """Garante que DatabaseError está importado no namespace de core.middleware evitando NameError."""
        from core import middleware
        self.assertTrue(
            hasattr(middleware, "DatabaseError"),
            "DatabaseError deve estar importado em core.middleware para capturar exceções de base de dados"
        )
        factory = RequestFactory()
        request = factory.get("/")
        mw = OrganizationMiddleware(lambda req: HttpResponse("ok"))
        with unittest.mock.patch("core.models.Organization.objects.filter", side_effect=DatabaseError("DB Failure")):
            with unittest.mock.patch("core.models.Organization.objects.first", side_effect=DatabaseError("DB Failure")):
                try:
                    mw(request)
                except NameError as ne:
                    self.fail(f"OrganizationMiddleware lançou NameError: {ne}")
                except Exception:
                    pass

    def test_middleware_ipv6_host_parsed_properly(self):
        """Host em formato IPv6 (RFC 2732 com parênteses retos [::1]) não pode ser truncado para '['."""
        factory = RequestFactory()
        request = factory.get("/dashboard/", HTTP_HOST="[::1]:8000")
        mw = OrganizationMiddleware(lambda req: HttpResponse("ok"))
        with unittest.mock.patch("core.models.Organization.objects.filter") as mock_filter:
            mock_filter.return_value.first.return_value = self.org
            mw(request)
            if mock_filter.called:
                _, called_kwargs = mock_filter.call_args
                domain_searched = called_kwargs.get("domain", "")
                self.assertNotEqual(
                    domain_searched, "[",
                    "Middleware não pode pesquisar por domain='[' ao receber host IPv6 bracketed"
                )

    @override_settings(ALLOWED_HOSTS=['127.0.0.1', 'localhost', 'testserver'])
    def test_health_check_responds_200_with_internal_ip(self):
        """Endpoint de verificação de saúde (/health/) deve responder com 200 mesmo quando invocado via IP de container/LAN."""
        res = self.client.get("/health/", HTTP_HOST="10.0.1.25")
        self.assertNotEqual(res.status_code, 400, "Health check não pode devolver 400 DisallowedHost para IPs internos")
        self.assertEqual(res.status_code, 200)


class AssociationVsProformPermissionsTestCase(TestCase):
    """
    Testes de Segregação de Permissões: Associação ACR vs ProForm.
    Garante que utilizadores do ProForm não acedem a áreas exclusivas da Associação ACR
    e que os membros da Direção da ACR mantêm a supervisão e controlo institucional.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="ACR & Proform Test", domain="testserver")

        # 1. Utilizador da Direção ACR
        self.acr_user = User.objects.create_user(
            username="direcao_acr",
            password="password123",
            email="direcao@acr.local"
        )
        self.acr_profile = UserProfile.objects.create(
            user=self.acr_user,
            organization=self.org,
            user_type=UserProfile.UserType.ACR_DIRECTION,
            entity_affiliation=UserProfile.EntityAffiliation.ACR_ONLY,
            can_view_finances=True,
            can_manage_bookings=True,
            can_view_all_clients=True,
            can_create_events=True
        )

        # 2. Utilizador do ProForm (Diretor Técnico / Treinador)
        self.proform_user = User.objects.create_user(
            username="treinador_proform",
            password="password123",
            email="treinador@proform.local"
        )
        self.proform_instructor = Instructor.objects.create(
            organization=self.org,
            first_name="Treinador",
            last_name="Proform",
            entity_affiliation=Instructor.EntityAffiliation.PROFORM_ONLY,
            is_technical_director=True
        )
        self.proform_profile = UserProfile.objects.create(
            user=self.proform_user,
            organization=self.org,
            user_type=UserProfile.UserType.PROFORM_DIRECTOR,
            entity_affiliation=UserProfile.EntityAffiliation.PROFORM_ONLY,
            instructor=self.proform_instructor,
            can_view_finances=True,
            can_manage_bookings=True,
            can_view_all_clients=True,
            can_create_events=True
        )

        # 3. Utilizador Cliente / Praticante comum
        self.client_user = User.objects.create_user(
            username="cliente_comum",
            password="password123",
            email="cliente@test.local"
        )
        self.client_profile = UserProfile.objects.create(
            user=self.client_user,
            organization=self.org,
            user_type=UserProfile.UserType.CLIENT,
            entity_affiliation=UserProfile.EntityAffiliation.BOTH
        )

        # Dados desportivos e associativos de teste
        self.modality = Modality.objects.create(organization=self.org, name="Judo ACR")
        self.athlete = Person.objects.create(
            organization=self.org,
            first_name="Atleta",
            last_name="Sócio",
            member_category=Person.MemberCategory.SOCIO,
            member_number=10,
            membership_fee_status=Person.MembershipFeeStatus.UP_TO_DATE,
            entity_affiliation=Person.EntityAffiliation.BOTH
        )

        self.client = Client()

    def test_acr_direction_can_access_governance(self):
        """Membro da Direção ACR tem acesso total ao painel de órgãos sociais (HTTP 200)."""
        self.client.login(username="direcao_acr", password="password123")
        res = self.client.get(reverse("core:association_governance"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Órgãos Sociais")

    def test_proform_user_blocked_from_governance(self):
        """Membro do ProForm é rigorosamente bloqueado de aceder aos órgãos sociais da ACR (HTTP 403)."""
        self.client.login(username="treinador_proform", password="password123")
        res = self.client.get(reverse("core:association_governance"))
        self.assertEqual(res.status_code, 403, "Utilizador do ProForm deve receber HTTP 403 em /association/governance/")

    def test_proform_user_cannot_alter_acr_membership_fees(self):
        """Formulário submetido por ProForm não altera o estatuto de quotas ou número de sócio da ACR."""
        from core.forms import PersonForm

        # Submissão por utilizador do ProForm tentando isentar quotas e mudar número de sócio
        form = PersonForm(
            data={
                "first_name": "Atleta",
                "last_name": "Sócio Alterado",
                "member_category": Person.MemberCategory.SOCIO,
                "member_number": 999,
                "membership_fee_status": Person.MembershipFeeStatus.EXEMPT,
                "entity_affiliation": Person.EntityAffiliation.BOTH,
                "status": Person.Status.ACTIVE,
                "regulation_accepted": True,
            },
            instance=self.athlete,
            organization=self.org,
            user=self.proform_user
        )
        self.assertTrue(form.is_valid(), f"Erros do formulário: {form.errors}")
        saved_athlete = form.save()

        # O nome é atualizado, mas os campos associativos preservam os valores originais da base de dados
        self.assertEqual(saved_athlete.last_name, "Sócio Alterado")
        self.assertEqual(saved_athlete.member_number, 10, "Número de sócio não pode ser adulterado por utilizador ProForm")
        self.assertEqual(saved_athlete.membership_fee_status, Person.MembershipFeeStatus.UP_TO_DATE, "Estado de quotas não pode ser alterado por ProForm")

    def test_proform_director_can_add_graduation(self):
        """Diretor Técnico ProForm tem permissão para registar graduações / exames de cinto."""
        self.client.login(username="treinador_proform", password="password123")
        res = self.client.post(
            reverse("core:athlete_graduation_add", kwargs={"pk": self.athlete.pk}),
            {
                "modality": self.modality.pk,
                "rank_name": "Cinto Laranja (4º Kyu)",
                "rank_order": "4",
                "awarded_date": "2026-09-05",
                "examiner_name": "Comissão Técnica ProForm",
            }
        )
        self.assertEqual(res.status_code, 302)
        self.athlete.refresh_from_db()
        self.assertEqual(self.athlete.current_belt, "Cinto Laranja (4º Kyu)")

    def test_protocol_supervision_access_matrix(self):
        """
        Direção ACR e Direção Técnica ProForm acedem à supervisão do protocolo (HTTP 200).
        Mas apenas a Direção ACR tem competência para aprovar e alterar o estado do fecho (require_approval_power).
        """
        from core.models import ProtocolPeriodSettlement
        settlement = ProtocolPeriodSettlement.objects.create(
            organization=self.org,
            period_start=timezone.now().date(),
            period_end=timezone.now().date(),
            status=ProtocolPeriodSettlement.Status.DRAFT
        )

        # 1. Direção ACR acede e aprova
        self.client.login(username="direcao_acr", password="password123")
        res_supervision = self.client.get(reverse("core:protocol_supervision"))
        self.assertEqual(res_supervision.status_code, 200)

        res_approve = self.client.post(reverse("core:protocol_settlement_toggle_status", kwargs={"settlement_id": settlement.pk}))
        self.assertEqual(res_approve.status_code, 302)
        settlement.refresh_from_db()
        self.assertEqual(settlement.status, ProtocolPeriodSettlement.Status.APPROVED)

        # 2. Direção ProForm acede à supervisão para conferência
        self.client.login(username="treinador_proform", password="password123")
        res_pf_supervision = self.client.get(reverse("core:protocol_supervision"))
        self.assertEqual(res_pf_supervision.status_code, 200)

        # 3. Mas Direção ProForm é bloqueada ao tentar alterar estado do fecho formal
        res_pf_approve = self.client.post(reverse("core:protocol_settlement_toggle_status", kwargs={"settlement_id": settlement.pk}))
        self.assertEqual(res_pf_approve.status_code, 403, "ProForm não pode aprovar/alterar fecho de contas do protocolo")

    def test_navbar_visibility_per_role(self):
        """O menu da Associação ACR não deve expor a governação estatutária a utilizadores ProForm."""
        # ACR Direção
        self.client.login(username="direcao_acr", password="password123")
        res_acr = self.client.get("/")
        self.assertContains(res_acr, "Órgãos Sociais & Mandatos")
        self.assertContains(res_acr, "Direção ACR")

        # ProForm
        self.client.login(username="treinador_proform", password="password123")
        res_pf = self.client.get("/")
        self.assertNotContains(res_pf, "Órgãos Sociais & Mandatos")
        self.assertContains(res_pf, "Dir. ProForm")



