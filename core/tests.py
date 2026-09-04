import json
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, Client, RequestFactory, override_settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.http import HttpResponse
from rest_framework.test import APITestCase

from django.core import mail
from notifications.models import NotificationLog

from .models import (
    Organization, Person, Event, Resource, Booking,
    Instructor, Modality, ClassGroup, PaymentPlan,
    ClientSubscription, CreditHistory, Payment, GoogleDriveSyncLog,
    InstructorCommission, ProtocolPeriodSettlement
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
        starts = timezone.now().replace(microsecond=0)
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


