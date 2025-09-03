from __future__ import annotations

# Core Django imports (models/validators/timezone)
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError

# Import validations (safe: service uses lazy model getters; no circular import)
from .services.scheduling import ensure_no_conflict, ensure_capacity


class Organization(models.Model):
    """Tenant entity identified by its domain name."""
    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=255, unique=True, help_text="Tenant domain (e.g., acr.local)")
    settings_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Person(models.Model):
    """Customer/athlete stored under a specific organization."""
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INACTIVE = "inactive", "Inativo"
        SUSPENDED = "suspended", "Suspenso"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    nif = models.CharField("NIF", max_length=20, blank=True, db_index=True)
    phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    # Novos campos
    date_of_birth = models.DateField("Data de Nascimento", null=True, blank=True)
    address = models.TextField("Morada", blank=True)
    emergency_contact = models.CharField("Contacto de Emergência", max_length=100, blank=True)
    photo = models.ImageField("Foto", upload_to='clients/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    last_activity = models.DateTimeField("Última Atividade", null=True, blank=True)

    class Meta:
        unique_together = [("organization", "email"), ("organization", "nif")]
        ordering = ["first_name", "last_name"]

    def __str__(self) -> str:
        n = f"{self.first_name} {self.last_name}".strip()
        return f"{n} ({self.organization.name})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Instructor(models.Model):
    """Personal trainers and instructors."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    first_name = models.CharField("Nome", max_length=120)
    last_name = models.CharField("Apelido", max_length=120, blank=True)
    email = models.EmailField("Email", blank=True)
    phone = models.CharField("Telefone", max_length=50, blank=True)
    specialties = models.TextField("Especialidades", blank=True)
    photo = models.ImageField("Foto", upload_to='instructors/', null=True, blank=True)
    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        unique_together = [("organization", "email")]
        ordering = ["first_name", "last_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Modality(models.Model):
    """Exercise modalities (Pilates, Weight Training, etc.)."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField("Nome", max_length=100)
    description = models.TextField("Descrição", blank=True)
    default_duration_minutes = models.PositiveIntegerField("Duração Padrão (min)", default=60)
    max_capacity = models.PositiveIntegerField("Capacidade Máxima", default=10)
    color = models.CharField("Cor", max_length=7, default="#0d6efd", help_text="Cor hexadecimal para o Gantt")
    is_active = models.BooleanField("Ativa", default=True)
    created_at = models.DateTimeField("Criada em", auto_now_add=True)

    class Meta:
        unique_together = [("organization", "name")]
        ordering = ["name"]
        verbose_name_plural = "Modalities"

    def __str__(self) -> str:
        return self.name


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
    """Bookable resource (room/court/etc.)."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    capacity = models.PositiveIntegerField(default=10)

    class Meta:
        unique_together = [("organization", "name")]

    def __str__(self) -> str:
        return f"{self.name} ({self.capacity})"


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
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT, related_name="events")
    title = models.CharField(max_length=140)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "starts_at"]),
            models.Index(fields=["organization", "resource", "starts_at"]),
        ]
        ordering = ["starts_at"]

    def __str__(self) -> str:
        return f"{self.title} @ {self.starts_at:%Y-%m-%d %H:%M}"

    def clean(self) -> None:
        """Validate chronological order, default capacity, and overlap."""
        if self.ends_at <= self.starts_at:
            raise ValidationError("ends_at must be after starts_at")
        if not self.capacity:
            self.capacity = self.resource.capacity
        from .services.scheduling import ensure_no_conflict
        ensure_no_conflict(self)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def bookings_count(self) -> int:
        """Count non-cancelled bookings."""
        return self.bookings.exclude(status=Booking.Status.CANCELLED).count()

    @property
    def is_full(self) -> bool:
        """True if capacity reached."""
        return self.bookings_count >= self.capacity


class Booking(models.Model):
    """Person reserves a seat in an event (enforces capacity)."""
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="bookings")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="bookings")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CONFIRMED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("event", "person")]  # one booking per person/event

    def __str__(self) -> str:
        return f"{self.person} => {self.event} ({self.status})"

    def clean(self) -> None:
        """Enforce event capacity."""
        ensure_capacity(self)


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
