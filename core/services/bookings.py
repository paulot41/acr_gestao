from dataclasses import dataclass

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ..models import Booking


@dataclass(frozen=True)
class CancelBookingResult:
    ok: bool
    message: str
    status_code: int


def _user_can_cancel(booking: Booking, user) -> bool:
    if user.is_staff or user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    person = getattr(profile, "person", None)
    if person and booking.person_id == person.id:
        return True
    return False


def cancel_booking(booking: Booking, user) -> CancelBookingResult:
    if not _user_can_cancel(booking, user):
        return CancelBookingResult(
            ok=False,
            message=_("Sem permissão para cancelar esta reserva"),
            status_code=403,
        )

    if booking.status == Booking.Status.CANCELLED:
        return CancelBookingResult(
            ok=False,
            message=_("Esta reserva já está cancelada"),
            status_code=400,
        )

    if not booking.can_be_cancelled():
        return CancelBookingResult(
            ok=False,
            message=_("Esta reserva já não pode ser cancelada"),
            status_code=400,
        )

    booking.status = Booking.Status.CANCELLED
    booking.cancelled_at = timezone.now()
    booking.save(update_fields=["status", "cancelled_at"])

    if booking.subscription_used:
        sub = booking.subscription_used
        credits_to_refund = booking.credits_used or 1
        credits_before = sub.remaining_credits or 0
        sub.remaining_credits = credits_before + credits_to_refund
        sub.save(update_fields=["remaining_credits"])

        from ..models import CreditHistory
        CreditHistory.objects.create(
            organization=booking.organization,
            person=booking.person,
            subscription=sub,
            booking=booking,
            action=CreditHistory.Action.REFUND,
            credits_amount=credits_to_refund,
            credits_before=credits_before,
            credits_after=sub.remaining_credits,
            description=f"Reembolso de cancelamento da aula {booking.event.title if booking.event else ''}",
        )

    return CancelBookingResult(
        ok=True,
        message=_("Reserva cancelada com sucesso"),
        status_code=200,
    )
