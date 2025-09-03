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
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    nif = models.CharField("NIF", max_length=20, blank=True, db_index=True)
    phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("organization", "email"), ("organization", "nif")]
        ordering = ["first_name", "last_name"]

    def __str__(self) -> str:
        n = f"{self.first_name} {self.last_name}".strip()
        return f"{n} ({self.organization.name})"


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
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=140)
    kind = models.CharField(max_length=30, choices=KIND_CHOICES, default="membership")

    class Meta:
        unique_together = [("organization", "name")]

    def __str__(self) -> str:
        return f"{self.name} @ {self.organization.name}"


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
        ensure_no_conflict(self)  # cross-object validation

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
