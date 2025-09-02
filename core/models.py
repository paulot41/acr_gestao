# add at top with other imports
from django.core.exceptions import ValidationError
from .services.scheduling import ensure_no_conflict, ensure_capacity

class Event(models.Model):
    # ... (rest unchanged)

    def clean(self) -> None:
        # Basic temporal validation
        if self.ends_at <= self.starts_at:
            raise ValidationError("ends_at must be greater than starts_at")
        if not self.capacity:
            self.capacity = self.resource.capacity
        # Cross-object constraint: prevent overlaps on same resource
        ensure_no_conflict(self)

class Booking(models.Model):
    # ... (rest unchanged)

    def clean(self) -> None:
        # Cross-object constraint: enforce capacity rules
        ensure_capacity(self)
