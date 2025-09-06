"""
Serviços para gestão de alertas automáticos e notificações.
"""
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from ..models import (
    SystemAlert, ClientSubscription, Person, CreditHistory,
    PaymentPlan, Booking, Organization
)


class AlertService:
    """Serviço para criar e gerir alertas automáticos."""

    @staticmethod
    def check_low_credits(organization: Organization, threshold: int = 3):
        """Verifica clientes com créditos baixos e cria alertas."""
        low_credit_subscriptions = ClientSubscription.objects.filter(
            organization=organization,
            status=ClientSubscription.Status.ACTIVE,
            payment_plan__plan_type=PaymentPlan.PlanType.CREDITS,
            remaining_credits__lte=threshold,
            remaining_credits__gt=0
        ).select_related('person', 'payment_plan')

        for subscription in low_credit_subscriptions:
            # Verificar se já existe alerta recente
            existing_alert = SystemAlert.objects.filter(
                organization=organization,
                person=subscription.person,
                alert_type=SystemAlert.AlertType.LOW_CREDITS,
                status__in=[SystemAlert.Status.PENDING, SystemAlert.Status.SENT],
                created_at__gte=timezone.now() - timedelta(days=1)
            ).exists()

            if not existing_alert:
                SystemAlert.objects.create(
                    organization=organization,
                    alert_type=SystemAlert.AlertType.LOW_CREDITS,
                    person=subscription.person,
                    title=f"Créditos Baixos - {subscription.person.full_name}",
                    message=f"O cliente {subscription.person.full_name} tem apenas {subscription.remaining_credits} créditos restantes no plano {subscription.payment_plan.name}.",
                    metadata={
                        'subscription_id': subscription.id,
                        'remaining_credits': subscription.remaining_credits,
                        'plan_name': subscription.payment_plan.name
                    }
                )

    @staticmethod
    def check_expiring_subscriptions(organization: Organization, days_ahead: int = 7):
        """Verifica subscrições a expirar e cria alertas."""
        expiring_date = timezone.now().date() + timedelta(days=days_ahead)

        expiring_subscriptions = ClientSubscription.objects.filter(
            organization=organization,
            status=ClientSubscription.Status.ACTIVE,
            end_date__lte=expiring_date,
            end_date__gte=timezone.now().date()
        ).select_related('person', 'payment_plan')

        for subscription in expiring_subscriptions:
            existing_alert = SystemAlert.objects.filter(
                organization=organization,
                person=subscription.person,
                alert_type=SystemAlert.AlertType.SUBSCRIPTION_EXPIRING,
                status__in=[SystemAlert.Status.PENDING, SystemAlert.Status.SENT],
                created_at__gte=timezone.now() - timedelta(days=1)
            ).exists()

            if not existing_alert:
                days_until_expiry = (subscription.end_date - timezone.now().date()).days
                SystemAlert.objects.create(
                    organization=organization,
                    alert_type=SystemAlert.AlertType.SUBSCRIPTION_EXPIRING,
                    person=subscription.person,
                    title=f"Subscrição a Expirar - {subscription.person.full_name}",
                    message=f"A subscrição {subscription.payment_plan.name} de {subscription.person.full_name} expira em {days_until_expiry} dias ({subscription.end_date}).",
                    metadata={
                        'subscription_id': subscription.id,
                        'days_until_expiry': days_until_expiry,
                        'expiry_date': subscription.end_date.isoformat()
                    }
                )

    @staticmethod
    def check_expired_credits(organization: Organization):
        """Verifica créditos expirados e cria alertas."""
        today = timezone.now().date()

        expired_subscriptions = ClientSubscription.objects.filter(
            organization=organization,
            status=ClientSubscription.Status.ACTIVE,
            payment_plan__plan_type=PaymentPlan.PlanType.CREDITS,
            credits_expire_date__lt=today,
            remaining_credits__gt=0
        ).select_related('person', 'payment_plan')

        for subscription in expired_subscriptions:
            # Criar histórico de expiração
            CreditHistory.objects.create(
                organization=organization,
                person=subscription.person,
                subscription=subscription,
                action=CreditHistory.Action.EXPIRE,
                credits_amount=-subscription.remaining_credits,
                credits_before=subscription.remaining_credits,
                credits_after=0,
                description=f"Créditos expirados em {today}"
            )

            # Criar alerta
            SystemAlert.objects.create(
                organization=organization,
                alert_type=SystemAlert.AlertType.CREDITS_EXPIRED,
                person=subscription.person,
                title=f"Créditos Expirados - {subscription.person.full_name}",
                message=f"{subscription.remaining_credits} créditos do plano {subscription.payment_plan.name} expiraram em {today}.",
                metadata={
                    'subscription_id': subscription.id,
                    'expired_credits': subscription.remaining_credits,
                    'expiry_date': today.isoformat()
                }
            )

            # Remover créditos expirados
            subscription.remaining_credits = 0
            subscription.save(update_fields=['remaining_credits'])

    @staticmethod
    def create_booking_reminder(booking: Booking, hours_before: int = 2):
        """Cria lembrete de reserva."""
        reminder_time = booking.event.starts_at - timedelta(hours=hours_before)

        if reminder_time > timezone.now():
            SystemAlert.objects.create(
                organization=booking.organization,
                alert_type=SystemAlert.AlertType.BOOKING_REMINDER,
                person=booking.person,
                title=f"Lembrete de Aula - {booking.event.title}",
                message=f"Tem uma aula marcada para {booking.event.starts_at.strftime('%d/%m/%Y às %H:%M')} - {booking.event.title}.",
                metadata={
                    'booking_id': booking.id,
                    'event_id': booking.event.id,
                    'event_time': booking.event.starts_at.isoformat()
                },
                scheduled_for=reminder_time
            )

    @staticmethod
    def run_daily_checks(organization: Organization):
        """Executa todas as verificações diárias de alertas."""
        AlertService.check_low_credits(organization)
        AlertService.check_expiring_subscriptions(organization)
        AlertService.check_expired_credits(organization)


class CreditHistoryService:
    """Serviço para gestão do histórico de créditos."""

    @staticmethod
    def log_credit_purchase(subscription: ClientSubscription, credits_purchased: int):
        """Regista compra de créditos."""
        CreditHistory.objects.create(
            organization=subscription.organization,
            person=subscription.person,
            subscription=subscription,
            action=CreditHistory.Action.PURCHASE,
            credits_amount=credits_purchased,
            credits_before=subscription.remaining_credits - credits_purchased,
            credits_after=subscription.remaining_credits,
            description=f"Compra de {credits_purchased} créditos - {subscription.payment_plan.name}"
        )

    @staticmethod
    def log_credit_usage(booking: Booking):
        """Regista uso de crédito numa reserva."""
        if booking.subscription_used:
            CreditHistory.objects.create(
                organization=booking.organization,
                person=booking.person,
                subscription=booking.subscription_used,
                booking=booking,
                action=CreditHistory.Action.USE,
                credits_amount=-booking.credits_used,
                credits_before=booking.subscription_used.remaining_credits + booking.credits_used,
                credits_after=booking.subscription_used.remaining_credits,
                description=f"Uso de {booking.credits_used} crédito(s) - {booking.event.title}"
            )

    @staticmethod
    def log_credit_refund(booking: Booking):
        """Regista reembolso de crédito por cancelamento."""
        if booking.subscription_used:
            CreditHistory.objects.create(
                organization=booking.organization,
                person=booking.person,
                subscription=booking.subscription_used,
                booking=booking,
                action=CreditHistory.Action.REFUND,
                credits_amount=booking.credits_used,
                credits_before=booking.subscription_used.remaining_credits - booking.credits_used,
                credits_after=booking.subscription_used.remaining_credits,
                description=f"Reembolso de {booking.credits_used} crédito(s) - {booking.event.title} (cancelamento)"
            )

    @staticmethod
    def get_client_credit_summary(person: Person, organization: Organization):
        """Obtém resumo de créditos de um cliente."""
        active_subscriptions = ClientSubscription.objects.filter(
            organization=organization,
            person=person,
            status=ClientSubscription.Status.ACTIVE,
            payment_plan__plan_type=PaymentPlan.PlanType.CREDITS
        ).select_related('payment_plan')

        total_credits = sum(sub.remaining_credits for sub in active_subscriptions)

        credit_history = CreditHistory.objects.filter(
            organization=organization,
            person=person
        ).order_by('-created_at')[:10]  # Últimos 10 registos

        return {
            'total_credits': total_credits,
            'active_subscriptions': active_subscriptions,
            'recent_history': credit_history
        }
