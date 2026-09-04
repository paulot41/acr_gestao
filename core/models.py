from __future__ import annotations

# Core Django imports (models/validators/timezone)
from django.db import models, DatabaseError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from decimal import Decimal
import logging
import uuid

# PostgreSQL search functionality (with fallback for SQLite/non-postgres environments)
try:
    from django.contrib.postgres.indexes import GinIndex
    from django.contrib.postgres.search import SearchVectorField, SearchVector
except (ImportError, Exception):
    from django.db.models import TextField as SearchVectorField
    from django.db.models import Index as GinIndex
    SearchVector = None

from .fields import OptionalSearchVectorField

# Pillow check with FileField fallback for lightweight local dev
try:
    from PIL import Image  # noqa: F401
    PhotoField = models.ImageField
except (ImportError, Exception):
    PhotoField = models.FileField

# Import validations (safe: service uses lazy model getters; no circular import)
from .services.scheduling import ensure_no_conflict, ensure_capacity

logger = logging.getLogger(__name__)


class Organization(models.Model):
    """Tenant entity identified by its domain name."""
    class Type(models.TextChoices):
        GYM = "gym", "Ginásio (ACR)"
        WELLNESS = "wellness", "Pilates/Wellness (Proform)"
        BOTH = "both", "Ambos (ACR + Proform)"

    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=255, unique=True, help_text="Tenant domain (e.g., acr.local)")
    org_type = models.CharField("Tipo de Organização", max_length=20, choices=Type.choices, default=Type.BOTH)
    settings_json = models.JSONField(default=dict, blank=True)

    # Branding por tenant (conforme patch)
    primary_color = models.CharField(max_length=7, default="#0d6efd")
    secondary_color = models.CharField(max_length=7, default="#6c757d")
    logo_svg = models.TextField(blank=True, help_text="Conteúdo SVG para branding no admin e dashboard.")

    # Configurações financeiras
    gym_monthly_fee = models.DecimalField(
        "Mensalidade Ginásio (ACR)",
        max_digits=10,
        decimal_places=2,
        default=30.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    wellness_monthly_fee = models.DecimalField(
        "Mensalidade Pilates (Proform)",
        max_digits=10,
        decimal_places=2,
        default=45.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_org_type_display()})"

    def get_protocol_config(self):
        """Retorna a configuração dinâmica do protocolo, criando com valores padrão se não existir."""
        config, _ = ProtocolConfiguration.objects.get_or_create(organization=self)
        return config


class Person(models.Model):
    """Customer/athlete stored under a specific organization."""
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INACTIVE = "inactive", "Inativo"
        SUSPENDED = "suspended", "Suspenso"

    class EntityAffiliation(models.TextChoices):
        ACR_ONLY = "acr_only", "Apenas ACR (Ginásio)"
        PROFORM_ONLY = "proform_only", "Apenas Proform (Pilates)"
        BOTH = "both", "ACR + Proform"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="people")
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    nif = models.CharField("NIF", max_length=20, blank=True, db_index=True)
    phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    # CRM: preferências e estado de ciclo de vida (conforme patch)
    lifecycle_stage = models.CharField(max_length=32, default="subscriber",
                                       help_text="subscriber|lead|member|churn_risk|churned")
    marketing_optin_email = models.BooleanField(default=False)
    marketing_optin_sms = models.BooleanField(default=False)

    # RGPD consentimentos (conforme patch)
    consent_terms = models.BooleanField(default=False)
    consent_privacy = models.BooleanField(default=False)
    consent_marketing = models.BooleanField(default=False)
    consent_rgpd = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)

    # Busca full-text (Postgres) (conforme patch)
    search = OptionalSearchVectorField(null=True, editable=False)

    # Novos campos existentes
    date_of_birth = models.DateField("Data de Nascimento", null=True, blank=True)
    address = models.TextField("Morada", blank=True)
    emergency_contact = models.CharField("Contacto de Emergência", max_length=100, blank=True)

    # Seguro Desportivo Obrigatório e Exame Médico
    insurance_policy = models.CharField("Apólice de Seguro", max_length=100, blank=True, help_text="Número da apólice do seguro desportivo")
    insurance_expiry = models.DateField("Validade do Seguro", null=True, blank=True, help_text="Data de expiração do seguro desportivo")
    medical_certificate_expiry = models.DateField("Validade do Atestado Médico", null=True, blank=True, help_text="Data de expiração do atestado/exame médico")

    # Encarregado de Educação (para praticantes menores de 18 anos)
    guardian_name = models.CharField("Nome do Encarregado de Educação", max_length=120, blank=True)
    guardian_phone = models.CharField("Telefone do Encarregado", max_length=50, blank=True)
    guardian_nif = models.CharField("NIF do Encarregado", max_length=20, blank=True)

    def _person_upload_to(instance, filename):
        return f"clients/org_{instance.organization_id}/{filename}"

    photo = PhotoField("Foto", upload_to=_person_upload_to, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    last_activity = models.DateTimeField("Última Atividade", null=True, blank=True)

    # Novo campo para multi-entidade
    entity_affiliation = models.CharField(
        "Afiliação", max_length=20, choices=EntityAffiliation.choices, default=EntityAffiliation.ACR_ONLY,
        help_text="A que entidade(s) o cliente está inscrito"
    )

    class MemberCategory(models.TextChoices):
        SOCIO = "socio", "Sócio Praticante (ACR)"
        NAO_SOCIO = "nao_socio", "Não Sócio Praticante"

    class MembershipFeeStatus(models.TextChoices):
        UP_TO_DATE = "up_to_date", "Quotas em Dia"
        OVERDUE = "overdue", "Quotas em Dívida"
        EXEMPT = "exempt", "Isento de Quotas"

    member_category = models.CharField(
        "Categoria de Praticante",
        max_length=20,
        choices=MemberCategory.choices,
        default=MemberCategory.NAO_SOCIO,
        help_text="Enquadramento associativo do praticante na ACR"
    )
    emergency_relationship = models.CharField(
        "Parentesco do Contacto de Emergência",
        max_length=60,
        blank=True,
        help_text="Ex: Pai, Mãe, Cônjuge"
    )
    image_consent = models.BooleanField(
        "Consentimento de Uso de Imagem",
        default=False,
        help_text="Autorização para captação e divulgação de fotos/vídeos em treinos"
    )
    regulation_accepted = models.BooleanField(
        "Regulamento Interno Aceite",
        default=True,
        help_text="Declaração de conhecimento e aceitação do regulamento da ACR"
    )

    # GESTÃO ASSOCIATIVA ACR (Sócios, Quotas e Cartão Digital)
    member_number = models.PositiveIntegerField(
        "Número de Sócio ACR",
        null=True,
        blank=True,
        db_index=True,
        help_text="Número sequencial oficial de associado da ACR"
    )
    admission_date = models.DateField(
        "Data de Admissão de Sócio",
        null=True,
        blank=True,
        help_text="Data em que foi admitido como sócio da ACR"
    )
    membership_fee_status = models.CharField(
        "Estado das Quotas",
        max_length=20,
        choices=MembershipFeeStatus.choices,
        default=MembershipFeeStatus.UP_TO_DATE
    )
    qr_code_token = models.CharField(
        "Token QR Check-in",
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text="Token seguro único para leitura de QR Code no cartão e quiosque"
    )
    current_belt = models.CharField(
        "Cinto / Graduação Atual",
        max_length=60,
        blank=True,
        help_text="Ex: Cinto Branco, Cinto Amarelo (7º Kyu), Cinto Negro 1º Dan"
    )

    class Meta:
        ordering = ["first_name", "last_name"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "member_number"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email"],
                name="unique_person_org_email",
                condition=~models.Q(email=""),
            ),
            models.UniqueConstraint(
                fields=["organization", "nif"],
                name="unique_person_org_nif",
                condition=~models.Q(nif=""),
            ),
        ]

    def __str__(self) -> str:
        n = f"{self.first_name} {self.last_name}".strip()
        num_str = f" [Sócio #{self.member_number}]" if self.member_number else ""
        return f"{n}{num_str} ({self.get_entity_affiliation_display()})"

    def save(self, *args, **kwargs):
        if not self.qr_code_token:
            self.qr_code_token = uuid.uuid4().hex

        # Atribuição sequencial de número de sócio para sócios da ACR se ainda não atribuído
        if self.member_category == self.MemberCategory.SOCIO and not self.member_number and self.organization_id:
            max_num = Person.objects.filter(organization_id=self.organization_id).aggregate(
                max_n=models.Max("member_number")
            )["max_n"] or 0
            self.member_number = max_num + 1

        super().save(*args, **kwargs)
        from django.db import connection
        if SearchVector is not None and connection.vendor == "postgresql":
            try:
                type(self).objects.filter(pk=self.pk).update(
                    search=SearchVector("first_name", "last_name", "email", "nif", config="portuguese")
                )
            except DatabaseError as e:
                logger.warning("Falha ao atualizar SearchVector para Person %s: %s", self.pk, e)
            except Exception:
                pass

    def ensure_qr_token(self) -> str:
        """Garante que o praticante tem um token de QR Code gerado."""
        if not self.qr_code_token:
            self.qr_code_token = uuid.uuid4().hex
            Person.objects.filter(pk=self.pk).update(qr_code_token=self.qr_code_token)
        return self.qr_code_token

    @property
    def voting_eligible(self) -> bool:
        """Verifica se o sócio tem direito de voto (maior de 18 anos, sócio ACR e quotas em dia)."""
        if self.member_category != self.MemberCategory.SOCIO:
            return False
        if self.is_minor:
            return False
        if self.membership_fee_status == "overdue":
            return False
        return True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_minor(self) -> bool:
        """Verifica se o atleta é menor de 18 anos."""
        if not self.date_of_birth:
            return False
        today = timezone.now().date()
        age = today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
        return age < 18

    @property
    def insurance_status(self) -> dict:
        """Retorna o estado do seguro desportivo com rótulo e classe visual."""
        if not self.insurance_expiry:
            return {'status': 'missing', 'label': 'Sem Seguro', 'badge': 'bg-secondary', 'is_valid': False}
        today = timezone.now().date()
        if self.insurance_expiry < today:
            return {'status': 'expired', 'label': f'Vencido ({self.insurance_expiry.strftime("%d/%m/%Y")})', 'badge': 'bg-danger', 'is_valid': False}
        days_left = (self.insurance_expiry - today).days
        if days_left <= 30:
            return {'status': 'expiring_soon', 'label': f'Expira em {days_left}d', 'badge': 'bg-warning text-dark', 'is_valid': True}
        return {'status': 'valid', 'label': f'Válido até {self.insurance_expiry.strftime("%d/%m/%Y")}', 'badge': 'bg-success', 'is_valid': True}

    @property
    def medical_status(self) -> dict:
        """Retorna o estado do atestado/exame médico."""
        if not self.medical_certificate_expiry:
            return {'status': 'missing', 'label': 'Sem Exame', 'badge': 'bg-secondary', 'is_valid': False}
        today = timezone.now().date()
        if self.medical_certificate_expiry < today:
            return {'status': 'expired', 'label': f'Vencido ({self.medical_certificate_expiry.strftime("%d/%m/%Y")})', 'badge': 'bg-danger', 'is_valid': False}
        days_left = (self.medical_certificate_expiry - today).days
        if days_left <= 30:
            return {'status': 'expiring_soon', 'label': f'Expira em {days_left}d', 'badge': 'bg-warning text-dark', 'is_valid': True}
        return {'status': 'valid', 'label': f'Válido até {self.medical_certificate_expiry.strftime("%d/%m/%Y")}', 'badge': 'bg-success', 'is_valid': True}

    @property
    def active_subscription(self):
        """Retorna a subscrição ativa mais recente."""
        return self.subscriptions.filter(status='active').order_by('-start_date').first()

    def get_monthly_fee(self) -> Decimal:
        """Calcular mensalidade baseada na afiliação."""
        if self.entity_affiliation == self.EntityAffiliation.ACR_ONLY:
            return Decimal(self.organization.gym_monthly_fee)
        elif self.entity_affiliation == self.EntityAffiliation.PROFORM_ONLY:
            return Decimal(self.organization.wellness_monthly_fee)
        elif self.entity_affiliation == self.EntityAffiliation.BOTH:
            return (
                Decimal(self.organization.gym_monthly_fee)
                + Decimal(self.organization.wellness_monthly_fee)
            )
        return Decimal("0.0")


class Instructor(models.Model):
    """Personal trainers and instructors."""
    class EntityAffiliation(models.TextChoices):
        ACR_ONLY = "acr_only", "Apenas ACR (Ginásio)"
        PROFORM_ONLY = "proform_only", "Apenas Proform (Pilates)"
        BOTH = "both", "ACR + Proform"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    first_name = models.CharField("Nome", max_length=120)
    last_name = models.CharField("Apelido", max_length=120, blank=True)
    email = models.EmailField("Email", blank=True)
    phone = models.CharField("Telefone", max_length=50, blank=True)
    specialties = models.TextField("Especialidades", blank=True)
    photo = PhotoField("Foto", upload_to='instructors/', null=True, blank=True)
    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    # Novo campo para multi-entidade
    entity_affiliation = models.CharField(
        "Afiliação", max_length=20, choices=EntityAffiliation.choices, default=EntityAffiliation.ACR_ONLY,
        help_text="Para que entidade(s) o instrutor trabalha"
    )

    # Configurações de comissão
    acr_commission_rate = models.DecimalField(
        "Comissão ACR (%)", max_digits=5, decimal_places=2, default=60.00,
        help_text="Percentagem que o instrutor recebe por aulas ACR"
    )
    proform_commission_rate = models.DecimalField(
        "Comissão Proform (%)", max_digits=5, decimal_places=2, default=70.00,
        help_text="Percentagem que o instrutor recebe por aulas Proform"
    )

    # Direção Técnica e Credenciação IPDJ
    is_technical_director = models.BooleanField(
        "Diretor Técnico",
        default=False,
        help_text="Indica se o instrutor exerce funções de Diretor Técnico do protocolo ou projeto"
    )
    ipdj_license_number = models.CharField(
        "N.º Cédula / Título Profissional IPDJ",
        max_length=50,
        blank=True,
        help_text="Ex: Cédula n.º 97575 emitida pelo IPDJ"
    )
    ipdj_license_expiry = models.DateField(
        "Validade da Cédula IPDJ",
        null=True,
        blank=True,
        help_text="Data de validade do título profissional"
    )
    ipdj_project_name = models.CharField(
        "Projeto / Enquadramento IPDJ",
        max_length=150,
        blank=True,
        help_text="Ex: Protocolo ACR-Proform, Projeto IPDJ Desporto para Todos"
    )

    class Meta:
        ordering = ["first_name", "last_name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email"],
                name="unique_instructor_org_email",
                condition=~models.Q(email=""),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_entity_affiliation_display()})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Modality(models.Model):
    """Exercise modalities (Pilates, Weight Training, etc.)."""
    class EntityType(models.TextChoices):
        ACR = "acr", "ACR (Ginásio)"
        PROFORM = "proform", "Proform (Pilates/Wellness)"
        BOTH = "both", "Ambas"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField("Nome", max_length=100)
    description = models.TextField("Descrição", blank=True)
    default_duration_minutes = models.PositiveIntegerField("Duração Padrão (min)", default=60)
    max_capacity = models.PositiveIntegerField("Capacidade Máxima", default=10)
    color = models.CharField("Cor", max_length=7, default="#0d6efd", help_text="Cor hexadecimal para o Gantt")
    is_active = models.BooleanField("Ativa", default=True)
    created_at = models.DateTimeField("Criada em", auto_now_add=True)

    # Campo para associar à entidade
    entity_type = models.CharField(
        "Entidade", max_length=20, choices=EntityType.choices, default=EntityType.ACR,
        help_text="A que entidade esta modalidade pertence"
    )

    class Meta:
        unique_together = [("organization", "name")]
        ordering = ["entity_type", "name"]
        verbose_name_plural = "Modalities"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_entity_type_display()})"


class Membership(models.Model):
    """Subscription/membership lifecycle per person and org."""
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="memberships")
    plan = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    starts_on = models.DateField(default=timezone.now)
    ends_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-starts_on"]

    def __str__(self) -> str:
        return f"{self.person} - {self.plan} ({self.status})"


class Product(models.Model):
    """Billable item (membership, drop-in, pack, etc.) scoped to org."""
    KIND_CHOICES = (
        ("membership", "Membership"),
        ("dropin", "Drop-in"),
        ("pack", "Pack"),
        ("other", "Other"),
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="other")  # Adicionar este campo
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_months = models.PositiveIntegerField()
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "name")]

    def __str__(self):
        return f"{self.name} - {self.organization}"


class Price(models.Model):
    """Time-bounded price for a product."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="prices")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=8, default="EUR")
    valid_from = models.DateField(default=timezone.now)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-valid_from"]

    def __str__(self) -> str:
        return f"{self.amount} {self.currency} for {self.product}"

    def is_active_on(self, day) -> bool:
        """True if price is effective on a given date."""
        if self.valid_to and day > self.valid_to:
            return False
        return self.valid_from <= day


class Resource(models.Model):
    """Bookable resource (room/court/etc.) - MELHORADO com suas sugestões."""
    class EntityType(models.TextChoices):
        ACR = "acr", "ACR (Ginásio)"
        PROFORM = "proform", "Proform (Pilates/Wellness)"
        BOTH = "both", "Ambas"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField("Nome do Espaço", max_length=120)
    description = models.TextField("Descrição", blank=True, help_text="Descrição detalhada do espaço")
    capacity = models.PositiveIntegerField("Capacidade Máxima", default=10, help_text="Número máximo de pessoas")

    # Novo: Associação à entidade
    entity_type = models.CharField(
        "Entidade", max_length=20, choices=EntityType.choices, default=EntityType.ACR,
        help_text="A que entidade este espaço pertence"
    )

    # Novos campos importantes
    is_available = models.BooleanField("Disponível", default=True, help_text="Se o espaço está disponível para uso")
    equipment_list = models.TextField("Equipamentos", blank=True, help_text="Lista de equipamentos disponíveis")
    special_features = models.TextField("Características Especiais", blank=True, help_text="Ar condicionado, espelhos, etc.")

    class FacilityType(models.TextChoices):
        MUNICIPAL_CESSION = "municipal_cession", "Cedência Municipal Gratuita"
        RENTED = "rented", "Arrendado / Alugado"
        OWNED = "owned", "Instalações Próprias"

    facility_type = models.CharField(
        "Regime de Instalações",
        max_length=30,
        choices=FacilityType.choices,
        default=FacilityType.MUNICIPAL_CESSION,
        help_text="Regime jurídico de utilização deste espaço"
    )
    cession_entity = models.CharField(
        "Entidade Cedente / Proprietário",
        max_length=150,
        blank=True,
        default="Município de Celorico de Basto",
        help_text="Ex: Município de Celorico de Basto, Junta de Freguesia, etc."
    )
    address = models.CharField(
        "Morada / Localização do Espaço",
        max_length=255,
        blank=True,
        help_text="Localização física do pavilhão ou sala"
    )

    # Campos de gestão
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        unique_together = [("organization", "name")]
        ordering = ["entity_type", "name"]
        verbose_name = "Espaço"
        verbose_name_plural = "Espaços"

    def __str__(self) -> str:
        return f"{self.name} - {self.get_entity_type_display()} (Cap. {self.capacity})"


# Modelo para turmas/grupos de clientes
class ClassGroup(models.Model):
    """Turmas/grupos de clientes para aulas em grupo."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField("Nome da Turma", max_length=120)
    description = models.TextField("Descrição", blank=True)
    modality = models.ForeignKey(Modality, on_delete=models.CASCADE, related_name="class_groups")
    instructor = models.ForeignKey(Instructor, on_delete=models.SET_NULL, null=True, blank=True, related_name="class_groups")

    # Configurações da turma
    max_students = models.PositiveIntegerField("Máximo de Alunos", default=10)
    level = models.CharField("Nível", max_length=50, blank=True, help_text="Iniciante, Intermédio, Avançado")

    # Membros da turma
    members = models.ManyToManyField(Person, blank=True, related_name="class_groups",
                                   help_text="Clientes inscritos nesta turma")

    # Status e datas
    is_active = models.BooleanField("Ativa", default=True)
    start_date = models.DateField("Data de Início", null=True, blank=True)
    end_date = models.DateField("Data de Fim", null=True, blank=True)

    created_at = models.DateTimeField("Criada em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizada em", auto_now=True)

    class Meta:
        unique_together = [("organization", "name")]
        ordering = ["modality", "name"]
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"

    def __str__(self) -> str:
        return f"{self.name} - {self.modality.name}"

    @property
    def current_members_count(self) -> int:
        return self.members.filter(status='active').count()

    @property
    def has_availability(self) -> bool:
        return self.current_members_count < self.max_students


class ClassTemplate(models.Model):
    """Template for recurring classes (default capacity/duration)."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=140)
    default_capacity = models.PositiveIntegerField(default=10)
    default_duration_minutes = models.PositiveIntegerField(default=60)

    def __str__(self) -> str:
        return self.title


class Event(models.Model):
    """Scheduled event in a resource window (enforces overlap rules)."""
    class EventType(models.TextChoices):
        GROUP_CLASS = "group_class", "Aula de Turma"
        INDIVIDUAL = "individual", "Aula Individual"
        OPEN_CLASS = "open_class", "Aula Aberta"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="events")
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT, related_name="events")
    modality = models.ForeignKey(Modality, on_delete=models.PROTECT, related_name="events", null=True, blank=True)
    instructor = models.ForeignKey(Instructor, on_delete=models.SET_NULL, related_name="events", null=True, blank=True)

    # NOVO: Suporte para turmas
    event_type = models.CharField("Tipo de Evento", max_length=20, choices=EventType.choices, default=EventType.OPEN_CLASS)
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, null=True, blank=True, related_name="events",
                                  help_text="Turma associada (para aulas de turma)")
    individual_client = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True, related_name="individual_events",
                                        help_text="Cliente individual (para aulas individuais)")

    title = models.CharField(max_length=140)
    description = models.TextField("Descrição", blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    # Recorrência
    recurrence_group_id = models.UUIDField("Identificador de Série Recorrente", null=True, blank=True, db_index=True)

    # Campos do patch
    waitlist_enabled = models.BooleanField(default=True)
    max_capacity = models.PositiveIntegerField(default=10)
    capacity = models.PositiveIntegerField(default=0)

    # Campos para integração Google Calendar (FASE 2)
    google_calendar_id = models.CharField("ID Google Calendar", max_length=255, blank=True, null=True,
                                        help_text="ID do evento no Google Calendar")
    google_calendar_sync_enabled = models.BooleanField("Sincronização Google Calendar", default=True,
                                                      help_text="Se deve sincronizar com Google Calendar")
    last_google_sync = models.DateTimeField("Última Sincronização Google", null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "starts_at"]),
            models.Index(fields=["organization", "resource", "starts_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="event_ends_after_starts",
            )
        ]
        ordering = ["starts_at"]

    def __str__(self) -> str:
        return f"{self.title} @ {self.starts_at:%Y-%m-%d %H:%M}"

    def clean(self) -> None:
        """Validate chronological order, default capacity, and overlap."""
        if self.ends_at <= self.starts_at:
            raise ValidationError("ends_at must be after starts_at")

        # Validações específicas por tipo de evento
        if self.event_type == self.EventType.GROUP_CLASS:
            if not self.class_group:
                raise ValidationError("Aulas de turma devem ter uma turma associada")
            if not self.capacity:
                self.capacity = self.class_group.max_students
        elif self.event_type == self.EventType.INDIVIDUAL:
            if not self.individual_client:
                raise ValidationError("Aulas individuais devem ter um cliente associado")
            self.capacity = 1
        else:  # OPEN_CLASS
            if not self.capacity and hasattr(self, 'resource') and self.resource:
                self.capacity = self.resource.capacity

        # Sincronizar capacity e max_capacity para evitar ambiguidade
        if not self.capacity and self.max_capacity:
            self.capacity = self.max_capacity
        self.max_capacity = self.capacity

        from .services.scheduling import ensure_no_conflict
        ensure_no_conflict(self)

    def save(self, *args, **kwargs):
        if not self.capacity:
            if self.event_type == self.EventType.GROUP_CLASS and self.class_group:
                self.capacity = self.class_group.max_students
            elif self.event_type == self.EventType.INDIVIDUAL:
                self.capacity = 1
            elif hasattr(self, 'resource') and self.resource:
                self.capacity = self.resource.capacity
        if not self.capacity and self.max_capacity:
            self.capacity = self.max_capacity
        self.max_capacity = self.capacity
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def bookings_count(self) -> int:
        """Count non-cancelled bookings."""
        return self.bookings.exclude(status=self.bookings.model.Status.CANCELLED).count()

    @property
    def is_full(self) -> bool:
        """True if capacity reached."""
        return self.bookings_count >= self.capacity

    @property
    def display_title(self) -> str:
        """Título personalizado baseado no tipo de evento."""
        if self.event_type == self.EventType.GROUP_CLASS and self.class_group:
            return f"{self.class_group.name} - {self.modality.name if self.modality else self.title}"
        elif self.event_type == self.EventType.INDIVIDUAL and self.individual_client:
            return f"{self.individual_client.full_name} - {self.modality.name if self.modality else self.title}"
        else:
            return self.title


class Booking(models.Model):
    """Reservas com lista de espera e auto-check-in por QR."""
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmada"
        WAITLIST = "waitlist", "Lista de espera"
        CANCELLED = "cancelled", "Cancelada"
        NO_SHOW = "no_show", "Falta"
        CHECKED_IN = "checked_in", "Check-in"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="bookings")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="bookings")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="bookings")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CONFIRMED)
    created_at = models.DateTimeField(auto_now_add=True)
    checkin_code = models.CharField(max_length=16, blank=True)

    # Novos campos para gestão de créditos
    subscription_used = models.ForeignKey(
        'ClientSubscription', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Subscrição utilizada para esta reserva"
    )
    credits_used = models.PositiveIntegerField("Créditos Utilizados", default=1)
    is_paid = models.BooleanField("Pago", default=False, help_text="Se foi pago fora do sistema de créditos")
    payment_amount = models.DecimalField("Valor Pago", max_digits=10, decimal_places=2, default=0.00)
    cancelled_at = models.DateTimeField("Cancelado em", null=True, blank=True)

    class Meta:
        unique_together = [("event","person")]
        indexes = [
            models.Index(fields=["organization","created_at"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.person} => {self.event} ({self.status})"

    def clean(self):
        ensure_no_conflict(self.event)
        ensure_capacity(self)
        # Validar créditos se usar subscrição
        if self.subscription_used and self.status == self.Status.CONFIRMED:
            if not self.subscription_used.has_credits():
                raise ValidationError("Subscrição não tem créditos suficientes.")

    def mark_checked_in(self):
        self.status = "checked_in"
        self.save(update_fields=["status"])

    def can_be_cancelled(self) -> bool:
        """Verifica se a reserva pode ser cancelada (ex: até 2h antes)."""
        if self.status == self.Status.CANCELLED:
            return False

        # Permitir cancelamento até 2 horas antes do evento
        return timezone.now() < (self.event.starts_at - timezone.timedelta(hours=2))


class Invoice(models.Model):
    """Basic invoice header."""
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="invoices")
    issue_date = models.DateField(default=timezone.now)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ["-issue_date", "-id"]

    def __str__(self) -> str:
        return f"Invoice #{self.pk or 'new'} - {self.person}"

    def recompute_total(self) -> None:
        """Recompute total from dependent items."""
        agg = sum((it.quantity * it.unit_price for it in self.items.all()), start=0)
        self.total = agg
        self.save(update_fields=["total"])


class InvoiceItem(models.Model):
    """Invoice line item."""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self) -> str:
        return f"{self.description} x{self.quantity}"

    def save(self, *args, **kwargs):
        """Auto-update invoice total after saving the line."""
        super().save(*args, **kwargs)
        self.invoice.recompute_total()


class Payment(models.Model):
    """Payment records for clients."""
    class Method(models.TextChoices):
        CASH = "cash", "Dinheiro"
        CARD = "card", "Cartão"
        TRANSFER = "transfer", "Transferência"
        MBWAY = "mbway", "MB WAY"
        OTHER = "other", "Outro"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        COMPLETED = "completed", "Pago"
        CANCELLED = "cancelled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField("Valor", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    method = models.CharField("Método", max_length=20, choices=Method.choices, default=Method.CASH)
    status = models.CharField("Estado", max_length=20, choices=Status.choices, default=Status.PENDING)
    description = models.CharField("Descrição", max_length=200, blank=True)
    due_date = models.DateField("Data de Vencimento", null=True, blank=True)
    paid_date = models.DateField("Data de Pagamento", null=True, blank=True)
    notes = models.TextField("Notas", blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.person.full_name} - €{self.amount} ({self.status})"

    def is_overdue(self) -> bool:
        """Check if payment is overdue."""
        if self.status == self.Status.COMPLETED or not self.due_date:
            return False
        return timezone.now().date() > self.due_date


class InstructorCommission(models.Model):
    """Comissões dos instrutores por aula/evento."""
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name="commissions")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="commissions")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    # Valores financeiros
    total_revenue = models.DecimalField(
        "Receita Total",
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    instructor_amount = models.DecimalField(
        "Valor Instrutor",
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    entity_amount = models.DecimalField(
        "Valor Entidade",
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    commission_rate = models.DecimalField(
        "Taxa Comissão (%)",
        max_digits=5,
        decimal_places=2,
        default=60.00,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
    )

    # Controlo
    is_paid = models.BooleanField("Pago", default=False)
    payment_date = models.DateField("Data Pagamento", null=True, blank=True)
    notes = models.TextField("Notas", blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        unique_together = [("instructor", "event")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.instructor.full_name} - {self.event.title} (€{self.instructor_amount})"

    def save(self, *args, **kwargs):
        """Calcular automaticamente os valores baseados na comissão."""
        if self.total_revenue and self.commission_rate:
            self.instructor_amount = (self.total_revenue * self.commission_rate) / 100
            self.entity_amount = self.total_revenue - self.instructor_amount
        super().save(*args, **kwargs)


class ProtocolPeriodSettlement(models.Model):
    """Fecho oficial de contas do Protocolo ACR & Proform SC por período."""
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        APPROVED = "approved", "Aprovado pela Direção"
        SETTLED = "settled", "Liquidado / Pago"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="protocol_settlements")
    title = models.CharField("Designação do Fecho", max_length=200, blank=True)
    period_start = models.DateField("Início do Período")
    period_end = models.DateField("Fim do Período")

    # Valores financeiros da partilha
    total_revenue = models.DecimalField(
        "Receita Bruta Total",
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    instructor_total = models.DecimalField(
        "Remuneração dos Instrutores",
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    proform_share = models.DecimalField(
        "Parcela Ginásio Proform SC",
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    acr_share = models.DecimalField(
        "Parcela Associação ACR",
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # Estado e Controlo
    status = models.CharField("Estado", max_length=15, choices=Status.choices, default=Status.DRAFT)
    settled_at = models.DateTimeField("Data de Liquidação", null=True, blank=True)
    notes = models.TextField("Notas de Fecho e Observações", blank=True)
    created_at = models.DateTimeField("Emitido em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ["-period_end", "-created_at"]
        verbose_name = "Fecho de Contas do Protocolo"
        verbose_name_plural = "Fechos de Contas do Protocolo"

    def __str__(self) -> str:
        return f"Fecho Protocolo: {self.period_start:%d/%m/%Y} a {self.period_end:%d/%m/%Y} (€{self.total_revenue})"

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"Fecho de Contas ({self.period_start.strftime('%m/%Y')})"
        super().save(*args, **kwargs)


class ProtocolConfiguration(models.Model):
    """
    Parametrização institucional, seguradora, mediação e regras financeiras do Protocolo.
    100% editável e dinâmico, permitindo mudar de seguradora, mediador, projeto IPDJ ou quota.
    """
    class InsuranceSplitMode(models.TextChoices):
        ANNUAL_DONATION = "annual_donation", "Doação Anual Integral (Proform doa prémio à ACR)"
        MONTHLY_AMORTIZATION = "monthly_amortization", "Amortização Mensal Fracionada (1/12 por mês)"

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="protocol_config")

    # 1. Dados Institucionais ACR
    acr_official_name = models.CharField(
        "Nome Oficial da Associação",
        max_length=200,
        default="ACR - Associação Cultural e Recreativa de Basto (Santa Tecla)"
    )
    acr_nipc = models.CharField("NIPC da ACR", max_length=20, default="510695744")
    acr_address = models.CharField("Sede da ACR", max_length=255, default="Lugar da Igreja, 4890-526 Basto (Santa Tecla)")
    acr_representative_name = models.CharField("Presidente da Direção da ACR", max_length=150, default="Paulo Sérgio da Cunha Teixeira")
    acr_representative_role = models.CharField("Cargo do Representante ACR", max_length=100, default="Presidente da Direção")

    # 2. Dados Parceiro Proform SC
    proform_official_name = models.CharField(
        "Designação do Ginásio Parceiro",
        max_length=200,
        default="PROFORM - Strength & Conditioning"
    )
    proform_nipc = models.CharField("NIPC do Parceiro", max_length=20, default="210263601")
    proform_address = models.CharField("Sede do Parceiro", max_length=255, default="Rua Senhora da Conceição 24, 4890-223 Celorico de Basto")
    proform_representative_name = models.CharField("Representante do Parceiro", max_length=150, default="Daniel Silvério Leite Coelho")
    proform_representative_role = models.CharField("Cargo do Representante Parceiro", max_length=100, default="Diretor Técnico")

    # 3. Direção Técnica e Projetos IPDJ
    active_technical_director = models.ForeignKey(
        "Instructor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_protocol_configs",
        verbose_name="Diretor Técnico Ativo"
    )
    active_ipdj_project = models.CharField(
        "Projeto / Enquadramento IPDJ Vigente",
        max_length=200,
        default="Protocolo de Desportos de Combate e Artes Marciais (ACR & Proform SC)",
        help_text="Designação do projeto ou candidatura ao IPDJ"
    )

    # 4. Apólice de Seguro Desportivo
    insurance_company = models.CharField("Companhia Seguradora", max_length=120, default="Generali Seguros, S.A.")
    insurance_policy_number = models.CharField("N.º da Apólice", max_length=60, default="0010189147")
    insurance_product_name = models.CharField("Produto / Opção da Apólice", max_length=150, default="AP DESP CULT RECREIO - Ginásios com artes marciais")
    insurance_policy_start = models.DateField("Início da Vigência", null=True, blank=True)
    insurance_policy_expiry = models.DateField("Renovação Anual / Fim", null=True, blank=True)
    insurance_annual_premium = models.DecimalField(
        "Prémio Anual do Seguro (€)",
        max_digits=10,
        decimal_places=2,
        default=Decimal("362.82"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Custo total anual do seguro a ser comparticipado pelo Proform à ACR"
    )
    insurance_base_insured_count = models.PositiveIntegerField("Número Base de Praticantes Segurados", default=25)
    insurance_claim_deadline_days = models.PositiveIntegerField("Prazo para Participação de Sinistros (dias)", default=3)

    # Capitais Segurados
    capital_death_disability = models.DecimalField("Capital Morte / Invalidez Permanente (€)", max_digits=10, decimal_places=2, default=Decimal("33500.00"))
    capital_treatment = models.DecimalField("Capital Despesas de Tratamento (€)", max_digits=10, decimal_places=2, default=Decimal("5500.00"))
    treatment_deductible = models.DecimalField("Franquia Despesas Tratamento (€)", max_digits=10, decimal_places=2, default=Decimal("75.00"))
    capital_funeral = models.DecimalField("Capital Despesas de Funeral (€)", max_digits=10, decimal_places=2, default=Decimal("3000.00"))

    # 5. Mediador / Ponto de Venda de Seguros
    broker_name = models.CharField("Mediador de Seguros", max_length=150, default="SPR AGENTE SEGUROS LDA")
    broker_asf_number = models.CharField("N.º Registo ASF do Mediador", max_length=50, default="4195560913")
    broker_phone = models.CharField("Telefone do Mediador", max_length=50, default="963 958 018")
    broker_address = models.CharField("Morada do Mediador", max_length=255, default="Av. João Pinto Ribeiro 98 Fracção A, 4890-221 Celorico de Basto")

    # 6. Regras Financeiras do Protocolo
    acr_admin_fee_per_athlete = models.DecimalField(
        "Quota Administrativa ACR por Atleta (€/mês)",
        max_digits=6,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Valor fixo mensal a transferir para a ACR por cada praticante ativo nas modalidades"
    )
    insurance_split_mode = models.CharField(
        "Modo de Repartição do Seguro",
        max_length=30,
        choices=InsuranceSplitMode.choices,
        default=InsuranceSplitMode.MONTHLY_AMORTIZATION,
        help_text="Como o custo da apólice é computado nos fechos periódicos"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Parametrização do Protocolo"
        verbose_name_plural = "Parametrizações do Protocolo"

    def __str__(self) -> str:
        return f"Configuração Protocolo ({self.organization.name})"


class GoogleCalendarConfig(models.Model):
    """Configuração OAuth2 para Google Calendar por organização."""
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="google_calendar_config")

    # OAuth2 Credentials
    client_id = models.CharField("Google Client ID", max_length=255, blank=True)
    client_secret = models.CharField("Google Client Secret", max_length=255, blank=True)

    # Tokens OAuth2
    access_token = models.TextField("Access Token", blank=True)
    refresh_token = models.TextField("Refresh Token", blank=True)
    token_expiry = models.DateTimeField("Token Expiry", null=True, blank=True)

    # Configurações de sincronização
    sync_enabled = models.BooleanField("Sincronização Ativa", default=False)
    auto_sync_events = models.BooleanField("Auto-Sincronizar Eventos", default=True)
    sync_interval_hours = models.PositiveIntegerField("Intervalo Sincronização (horas)", default=1)

    # Metadados
    last_sync = models.DateTimeField("Última Sincronização", null=True, blank=True)
    sync_errors = models.TextField("Erros de Sincronização", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração Google Calendar"
        verbose_name_plural = "Configurações Google Calendar"

    def __str__(self):
        return f"Google Calendar - {self.organization.name}"

    @property
    def is_token_valid(self):
        """Verifica se o token ainda é válido."""
        if not self.token_expiry:
            return False
        return timezone.now() < self.token_expiry


class InstructorGoogleCalendar(models.Model):
    """Configuração individual de calendário para cada instrutor."""
    instructor = models.OneToOneField(Instructor, on_delete=models.CASCADE, related_name="google_calendar")

    # ID do calendário Google específico do instrutor
    google_calendar_id = models.CharField("ID Calendário Google", max_length=255, blank=True,
                                        help_text="ID do calendário Google específico do instrutor")

    # Configurações de sincronização
    sync_enabled = models.BooleanField("Sincronização Ativa", default=True)
    calendar_name = models.CharField("Nome do Calendário", max_length=100, blank=True,
                                   help_text="Nome do calendário no Google (auto-gerado se vazio)")
    calendar_color = models.CharField("Cor do Calendário", max_length=20, default="#0d6efd")

    # Configurações de privacidade
    share_with_organization = models.BooleanField("Partilhar com Organização", default=True)
    public_calendar = models.BooleanField("Calendário Público", default=False)

    # Filtros de sincronização
    sync_acr_events = models.BooleanField("Sincronizar Eventos ACR", default=True)
    sync_proform_events = models.BooleanField("Sincronizar Eventos Proform", default=True)

    # Metadados
    last_sync = models.DateTimeField("Última Sincronização", null=True, blank=True)
    sync_errors = models.TextField("Erros de Sincronização", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Calendário Google do Instrutor"
        verbose_name_plural = "Calendários Google dos Instrutores"

    def __str__(self):
        return f"Google Calendar - {self.instructor.full_name}"

    def get_calendar_name(self):
        """Gera nome do calendário se não especificado."""
        if self.calendar_name:
            return self.calendar_name
        return f"{self.instructor.full_name} - Aulas"


class GoogleCalendarSyncLog(models.Model):
    """Log de sincronizações com Google Calendar."""

    class SyncType(models.TextChoices):
        CREATE = "create", "Criar"
        UPDATE = "update", "Atualizar"
        DELETE = "delete", "Eliminar"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        SUCCESS = "success", "Sucesso"
        ERROR = "error", "Erro"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, null=True, blank=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)

    sync_type = models.CharField("Tipo de Sincronização", max_length=10, choices=SyncType.choices)
    status = models.CharField("Estado", max_length=10, choices=Status.choices, default=Status.PENDING)

    google_event_id = models.CharField("Google Event ID", max_length=255, blank=True)
    google_calendar_id = models.CharField("Google Calendar ID", max_length=255, blank=True)

    sync_data = models.JSONField("Dados de Sincronização", default=dict, blank=True)
    error_message = models.TextField("Mensagem de Erro", blank=True)

    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    processed_at = models.DateTimeField("Processado em", null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Log de Sincronização"
        verbose_name_plural = "Logs de Sincronização"

    def __str__(self):
        return f"{self.get_sync_type_display()} - {self.get_status_display()} ({self.created_at})"


class GoogleDriveSyncLog(models.Model):
    """Log de sincronização da lista de praticantes com Google Drive / Google Sheets da ACR."""
    class Status(models.TextChoices):
        SUCCESS = "success", "Sucesso"
        WARNING = "warning", "Aviso / Parcial"
        ERROR = "error", "Erro"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="drive_sync_logs")
    athletes_count = models.PositiveIntegerField("Atletas Sincronizados", default=0)
    status = models.CharField("Estado", max_length=10, choices=Status.choices, default=Status.SUCCESS)
    file_name = models.CharField("Ficheiro / Planilha", max_length=255, blank=True)
    google_sheet_id = models.CharField("ID da Google Sheet", max_length=255, blank=True)
    details = models.TextField("Detalhes", blank=True)
    created_at = models.DateTimeField("Data de Sincronização", auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Log de Sincronização Google Drive"
        verbose_name_plural = "Logs de Sincronização Google Drive"

    def __str__(self):
        return f"Sync Drive ({self.athletes_count} atletas) - {self.get_status_display()} em {self.created_at:%d/%m/%Y %H:%M}"


# Adicionar antes do modelo Payment
class PaymentPlan(models.Model):
    """Planos de pagamento flexíveis para mensalidades e créditos."""
    class PlanType(models.TextChoices):
        MONTHLY = "monthly", "Mensalidade"
        CREDITS = "credits", "Créditos para Aulas"
        UNLIMITED = "unlimited", "Ilimitado"

    class EntityType(models.TextChoices):
        ACR = "acr", "ACR (Ginásio)"
        PROFORM = "proform", "Proform (Pilates/Wellness)"
        BOTH = "both", "Ambas"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField("Nome do Plano", max_length=120)
    description = models.TextField("Descrição", blank=True)
    plan_type = models.CharField("Tipo de Plano", max_length=20, choices=PlanType.choices, default=PlanType.MONTHLY)
    entity_type = models.CharField("Entidade", max_length=20, choices=EntityType.choices, default=EntityType.ACR)

    # Preço e duração
    price = models.DecimalField("Preço", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    duration_months = models.PositiveIntegerField("Duração (meses)", default=1, help_text="Para planos mensais")

    # Campos específicos para planos de crédito
    credits_included = models.PositiveIntegerField("Créditos Incluídos", default=0, help_text="Número de aulas incluídas")
    credits_validity_days = models.PositiveIntegerField("Validade dos Créditos (dias)", default=30, help_text="Dias para usar os créditos")

    # Modalidades aplicáveis (para planos específicos)
    modalities = models.ManyToManyField(Modality, blank=True, help_text="Modalidades incluídas neste plano")

    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        unique_together = [("organization", "name")]
        ordering = ["entity_type", "plan_type", "name"]
        verbose_name = "Plano de Pagamento"
        verbose_name_plural = "Planos de Pagamento"

    def __str__(self) -> str:
        return f"{self.name} - {self.get_plan_type_display()} ({self.get_entity_type_display()})"


class ClientSubscription(models.Model):
    """Subscrições ativas dos clientes aos planos de pagamento."""
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        EXPIRED = "expired", "Expirado"
        SUSPENDED = "suspended", "Suspenso"
        CANCELLED = "cancelled", "Cancelado"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="subscriptions")
    payment_plan = models.ForeignKey(PaymentPlan, on_delete=models.PROTECT, related_name="subscriptions")

    status = models.CharField("Estado", max_length=20, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField("Data de Início", default=timezone.now)
    end_date = models.DateField("Data de Fim", null=True, blank=True)

    # Créditos (para planos de crédito)
    remaining_credits = models.PositiveIntegerField("Créditos Restantes", default=0)
    credits_expire_date = models.DateField("Data de Expiração dos Créditos", null=True, blank=True)

    # Controlo de pagamentos
    is_paid = models.BooleanField("Pago", default=False)
    payment_date = models.DateField("Data de Pagamento", null=True, blank=True)

    notes = models.TextField("Notas", blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Subscrição de Cliente"
        verbose_name_plural = "Subscrições de Clientes"

    def __str__(self) -> str:
        return f"{self.person.full_name} - {self.payment_plan.name} ({self.status})"

    def is_active(self) -> bool:
        """Verifica se a subscrição está ativa e válida."""
        if self.status != self.Status.ACTIVE:
            return False
        if self.end_date and timezone.now().date() > self.end_date:
            return False
        return True

    def has_credits(self) -> bool:
        """Verifica se ainda tem créditos disponíveis."""
        if self.payment_plan.plan_type != PaymentPlan.PlanType.CREDITS:
            return True  # Planos mensais/ilimitados sempre "têm créditos"
        return self.remaining_credits > 0

    def use_credit(self) -> bool:
        """Usa um crédito se disponível. Retorna True se conseguiu usar."""
        if not self.has_credits():
            return False
        if self.payment_plan.plan_type == PaymentPlan.PlanType.CREDITS:
            self.remaining_credits -= 1
            self.save(update_fields=['remaining_credits'])
        return True


# Modelo para gerir perfis de utilizador com permissões
class UserProfile(models.Model):
    """Perfil de utilizador com permissões específicas."""
    class UserType(models.TextChoices):
        ADMIN = "admin", "Administrador Total"
        STAFF = "staff", "Staff (Leitura + Marcações)"
        INSTRUCTOR = "instructor", "Instrutor"
        CLIENT = "client", "Cliente"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user_type = models.CharField("Tipo de Utilizador", max_length=20, choices=UserType.choices, default=UserType.CLIENT)

    # Associação com Person/Instructor se aplicável
    person = models.OneToOneField(Person, on_delete=models.CASCADE, null=True, blank=True, related_name="user_profile")
    instructor = models.OneToOneField(Instructor, on_delete=models.CASCADE, null=True, blank=True, related_name="user_profile")

    # Permissões específicas para staff
    can_view_finances = models.BooleanField("Ver Finanças", default=False)
    can_manage_bookings = models.BooleanField("Gerir Marcações", default=True)
    can_view_all_clients = models.BooleanField("Ver Todos os Clientes", default=True)
    can_create_events = models.BooleanField("Criar Eventos", default=False)

    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        unique_together = [("organization", "user")]
        verbose_name = "Perfil de Utilizador"
        verbose_name_plural = "Perfis de Utilizadores"

    def __str__(self) -> str:
        return f"{self.user.get_full_name() or self.user.username} - {self.get_user_type_display()}"

    def has_admin_access(self) -> bool:
        """Verifica se tem acesso total de administração."""
        return self.user_type == self.UserType.ADMIN

    def can_access_admin(self) -> bool:
        """Verifica se pode aceder ao painel admin."""
        return self.user_type in [self.UserType.ADMIN, self.UserType.STAFF]


# Modelo para histórico de consumo de créditos
class CreditHistory(models.Model):
    """Histórico de uso de créditos pelos clientes."""
    class Action(models.TextChoices):
        PURCHASE = "purchase", "Compra de Créditos"
        USE = "use", "Uso de Crédito"
        REFUND = "refund", "Reembolso"
        EXPIRE = "expire", "Expiração"
        TRANSFER = "transfer", "Transferência"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="credit_history")
    subscription = models.ForeignKey(ClientSubscription, on_delete=models.CASCADE, related_name="credit_history")
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name="credit_history")

    action = models.CharField("Ação", max_length=20, choices=Action.choices)
    credits_amount = models.IntegerField("Quantidade de Créditos", help_text="Positivo para adicionar, negativo para remover")
    credits_before = models.PositiveIntegerField("Créditos Antes", default=0)
    credits_after = models.PositiveIntegerField("Créditos Depois", default=0)

    description = models.CharField("Descrição", max_length=200, blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Histórico de Créditos"
        verbose_name_plural = "Histórico de Créditos"

    def __str__(self) -> str:
        return f"{self.person.full_name} - {self.get_action_display()} ({self.credits_amount:+d})"


# Modelo para alertas de sistema
class SystemAlert(models.Model):
    """Alertas automáticos do sistema."""
    class AlertType(models.TextChoices):
        LOW_CREDITS = "low_credits", "Créditos Baixos"
        SUBSCRIPTION_EXPIRING = "subscription_expiring", "Subscrição a Expirar"
        PAYMENT_OVERDUE = "payment_overdue", "Pagamento em Atraso"
        BOOKING_REMINDER = "booking_reminder", "Lembrete de Reserva"
        CREDITS_EXPIRED = "credits_expired", "Créditos Expirados"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        SENT = "sent", "Enviado"
        READ = "read", "Lido"
        DISMISSED = "dismissed", "Ignorado"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    alert_type = models.CharField("Tipo de Alerta", max_length=30, choices=AlertType.choices)
    status = models.CharField("Estado", max_length=20, choices=Status.choices, default=Status.PENDING)

    # Destinatários
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts")

    # Dados do alerta
    title = models.CharField("Título", max_length=200)
    message = models.TextField("Mensagem")
    metadata = models.JSONField("Metadados", default=dict, blank=True, help_text="Dados adicionais do alerta")

    # Controlo de envio
    scheduled_for = models.DateTimeField("Agendado para", null=True, blank=True)
    sent_at = models.DateTimeField("Enviado em", null=True, blank=True)
    read_at = models.DateTimeField("Lido em", null=True, blank=True)

    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Alerta do Sistema"
        verbose_name_plural = "Alertas do Sistema"

    def __str__(self) -> str:
        return f"{self.get_alert_type_display()} - {self.title}"

    def mark_as_read(self):
        """Marca o alerta como lido."""
        if self.status in [self.Status.SENT, self.Status.PENDING]:
            self.status = self.Status.READ
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])

    def dismiss(self):
        """Ignora o alerta."""
        self.status = self.Status.DISMISSED
        self.save(update_fields=['status'])


# Novos modelos CRM e Marketing (conforme patch)
class Campaign(models.Model):
    """Marketing: campanhas de email/SMS segmentadas por tenant."""
    CHANNELS = (("email","Email"),("sms","SMS"))
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="campaigns")
    name = models.CharField(max_length=150)
    channel = models.CharField(max_length=16, choices=CHANNELS)
    segment_query = models.JSONField(default=dict, help_text="Ex: {status:'active', lifecycle_stage:'lead'}")
    subject = models.CharField(max_length=200, blank=True)
    content = models.TextField(help_text="Template Jinja/Django para envio.")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_channel_display()}) - {self.organization.name}"


class MessageLog(models.Model):
    """Histórico de envios (auditoria/RGPD)."""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="logs")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="message_logs")
    channel = models.CharField(max_length=16)
    status = models.CharField(max_length=32, default="queued")  # queued|sent|failed|opened|clicked|unsubscribed
    provider_message_id = models.CharField(max_length=128, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.campaign.name} -> {self.person.full_name} ({self.status})"


# ==============================================================================
# GESTÃO DESPORTIVA: GRADUAÇÕES & CINTOS DE ARTES MARCIAIS
# ==============================================================================

class AthleteGraduation(models.Model):
    """Registo histórico de graduação / exame de cinto de um atleta."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="graduations")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="graduations")
    modality = models.ForeignKey(Modality, on_delete=models.CASCADE, related_name="graduations")
    rank_name = models.CharField("Graduação / Cinto", max_length=60, help_text="Ex: Cinto Branco, Cinto Amarelo (7º Kyu), Cinto Negro 1º Dan")
    rank_order = models.PositiveIntegerField("Ordem do Cinto", default=1, help_text="1=Branco, 2=Amarelo, 3=Laranja, etc.")
    awarded_date = models.DateField("Data do Exame / Atribuição")
    examiner = models.ForeignKey(Instructor, on_delete=models.SET_NULL, null=True, blank=True, related_name="awarded_graduations")
    examiner_name = models.CharField("Examinador / Mestre", max_length=120, blank=True)
    certificate_number = models.CharField("N.º de Diploma / Certificado", max_length=60, blank=True)
    classes_attended_count = models.PositiveIntegerField("Treinos Cumpridos", default=0, help_text="Aulas contabilizadas no tapete até a este exame")
    notes = models.TextField("Notas de Avaliação Técnica", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-awarded_date", "-rank_order"]
        verbose_name = "Graduação / Exame de Cinto"
        verbose_name_plural = "Graduações / Exames de Cinto"
        indexes = [
            models.Index(fields=["organization", "person"]),
            models.Index(fields=["person", "modality"]),
        ]

    def __str__(self) -> str:
        return f"{self.person.full_name} - {self.rank_name} ({self.modality.name})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Sincronizar graduação atual na ficha do atleta
        if self.rank_name and self.person_id:
            Person.objects.filter(pk=self.person_id).update(current_belt=self.rank_name)


# ==============================================================================
# GESTÃO DA ASSOCIAÇÃO ACR: GOVERNANÇA, ÓRGÃOS SOCIAIS & MANDATOS
# ==============================================================================

class GoverningBody(models.Model):
    """Órgão Social estatutário da Associação ACR (Direção, Assembleia Geral, Conselho Fiscal)."""
    class BodyType(models.TextChoices):
        BOARD = "board", "Direção"
        GENERAL_ASSEMBLY = "general_assembly", "Mesa da Assembleia Geral"
        FISCAL_COUNCIL = "fiscal_council", "Conselho Fiscal"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="governing_bodies")
    body_type = models.CharField("Órgão Social", max_length=30, choices=BodyType.choices, default=BodyType.BOARD)
    term_label = models.CharField("Mandato", max_length=60, default="2024–2028")
    start_date = models.DateField("Data de Início / Posse")
    end_date = models.DateField("Data de Término do Mandato")
    election_date = models.DateField("Data da Eleição", null=True, blank=True)
    is_active = models.BooleanField("Mandato em Funções", default=True)
    electoral_minutes_ref = models.CharField("Referência da Ata Eleitoral", max_length=120, blank=True, help_text="Ex: Ata n.º 12/2024 da Assembleia Eleitoral")
    notes = models.TextField("Observações / Competências Estatutárias", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["body_type", "-start_date"]
        verbose_name = "Órgão Social"
        verbose_name_plural = "Órgãos Sociais"

    def __str__(self) -> str:
        return f"{self.get_body_type_display()} ({self.term_label})"


class GoverningBodyMember(models.Model):
    """Membro titular eleito para um Órgão Social da ACR."""
    governing_body = models.ForeignKey(GoverningBody, on_delete=models.CASCADE, related_name="members")
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="governing_roles")
    name = models.CharField("Nome do Titular", max_length=140)
    role = models.CharField("Cargo", max_length=80)  # Presidente, Vice-Presidente, Tesoureiro, Secretário, Vogal, Relator
    order = models.PositiveIntegerField("Ordem de Precedência", default=1)
    notes = models.CharField("Observações", max_length=200, blank=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Titular de Órgão Social"
        verbose_name_plural = "Titulares de Órgãos Sociais"

    def __str__(self) -> str:
        return f"{self.role}: {self.name} ({self.governing_body.get_body_type_display()})"

