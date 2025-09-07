"""
Vistas específicas para dashboards personalizados por tipo de utilizador.
Dashboard simplificado para consulta e marcação de aulas - operações CRUD no Django Admin.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from .models import (
    Person, Instructor, Event, Booking, ClientSubscription,
    SystemAlert, UserProfile
)
from .services.alerts import AlertService, CreditHistoryService


@login_required
def dashboard_router(request):
    """Dashboard unificado: redireciona para o Gantt para consulta/marcação de aulas."""
    return redirect('core:gantt')


@login_required
def dashboard_admin(request):
    """Dashboard simplificado para administradores - consulta apenas."""
    org = request.organization

    # Executar verificações diárias de alertas
    try:
        AlertService.run_daily_checks(org)
    except Exception:
        pass  # Não bloquear dashboard se alertas falharem

    # Estatísticas básicas para hoje
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())

    try:
        stats = {
            'total_clients': Person.objects.filter(organization=org, status='active').count(),
            'total_instructors': Instructor.objects.filter(organization=org, is_active=True).count(),
            'todays_events': Event.objects.filter(
                organization=org,
                starts_at__date=today
            ).count(),
            'weekly_revenue': ClientSubscription.objects.filter(
                organization=org,
                payment_date__gte=week_start,
                is_paid=True
            ).aggregate(Sum('payment_plan__price'))['payment_plan__price__sum'] or 0,
        }

        # Próximos eventos (hoje apenas)
        upcoming_events = Event.objects.filter(
            organization=org,
            starts_at__date=today
        ).select_related('resource', 'instructor', 'modality').order_by('starts_at')[:10]

        # Alertas críticos apenas
        critical_alerts = SystemAlert.objects.filter(
            organization=org,
            status=SystemAlert.Status.PENDING,
            alert_type__in=[
                SystemAlert.AlertType.LOW_CREDITS,
                SystemAlert.AlertType.SUBSCRIPTION_EXPIRING
            ]
        ).order_by('-created_at')[:5]

    except Exception as e:
        messages.error(request, f"Erro ao carregar dados: {str(e)}")
        stats = {'total_clients': 0, 'total_instructors': 0, 'todays_events': 0, 'weekly_revenue': 0}
        upcoming_events = []
        critical_alerts = []

    context = {
        'stats': stats,
        'upcoming_events': upcoming_events,
        'alerts': critical_alerts,
        'dashboard_type': 'admin',
        'admin_url': '/admin/',  # Link para Django admin
    }

    return render(request, 'core/dashboard_simple.html', context)


@login_required
def dashboard_instructor(request):
    """Dashboard simplificado para instrutores - apenas suas aulas."""
    try:
        profile = request.user.profile
        if not hasattr(profile, 'instructor') or not profile.instructor:
            messages.error(request, "Perfil de instrutor não encontrado.")
            return redirect('core:dashboard')

        instructor = profile.instructor
        org = request.organization
        today = timezone.now().date()

        # Aulas de hoje do instrutor
        todays_classes = Event.objects.filter(
            organization=org,
            instructor=instructor,
            starts_at__date=today
        ).select_related('resource', 'modality').order_by('starts_at')

        # Próximas aulas (próximos 3 dias)
        upcoming_classes = Event.objects.filter(
            organization=org,
            instructor=instructor,
            starts_at__date__gt=today,
            starts_at__date__lte=today + timedelta(days=3)
        ).select_related('resource', 'modality').order_by('starts_at')[:5]

        stats = {
            'todays_classes': todays_classes.count(),
            'upcoming_classes': upcoming_classes.count(),
        }

        context = {
            'instructor': instructor,
            'stats': stats,
            'todays_classes': todays_classes,
            'upcoming_classes': upcoming_classes,
            'dashboard_type': 'instructor'
        }

        return render(request, 'core/dashboard_simple.html', context)

    except Exception as e:
        messages.error(request, f"Erro ao carregar dashboard: {str(e)}")
        return redirect('core:dashboard')


@login_required
def dashboard_client(request):
    """Dashboard simplificado para clientes - consulta de reservas e marcação via Gantt."""
    try:
        profile = request.user.profile
        if not hasattr(profile, 'person') or not profile.person:
            messages.error(request, "Perfil de cliente não encontrado.")
            return redirect('core:dashboard')

        person = profile.person
        org = request.organization

        # Próximas reservas (máximo 5)
        upcoming_bookings = Booking.objects.filter(
            organization=org,
            person=person,
            status='confirmed',
            event__starts_at__gte=timezone.now()
        ).select_related('event', 'event__resource', 'event__modality').order_by('event__starts_at')[:5]

        # Resumo básico de créditos
        try:
            credit_summary = CreditHistoryService.get_client_credit_summary(person, org)
        except Exception:
            credit_summary = {'total_credits': 0}

        # Subscrições ativas
        active_subscriptions = ClientSubscription.objects.filter(
            organization=org,
            person=person,
            status='active'
        ).select_related('payment_plan')

        stats = {
            'upcoming_bookings': upcoming_bookings.count(),
            'total_credits': credit_summary.get('total_credits', 0),
            'active_plans': active_subscriptions.count()
        }

        context = {
            'person': person,
            'stats': stats,
            'upcoming_bookings': upcoming_bookings,
            'active_subscriptions': active_subscriptions,
            'dashboard_type': 'client'
        }

        return render(request, 'core/dashboard_simple.html', context)

    except Exception as e:
        messages.error(request, f"Erro ao carregar dashboard: {str(e)}")
        return redirect('core:dashboard')


@login_required
def dashboard_staff(request):
    """Dashboard simplificado para staff - eventos de hoje apenas."""
    org = request.organization
    today = timezone.now().date()

    try:
        # Eventos de hoje
        todays_events = Event.objects.filter(
            organization=org,
            starts_at__date=today
        ).select_related('resource', 'instructor', 'modality').order_by('starts_at')

        # Reservas de hoje
        todays_bookings = Booking.objects.filter(
            organization=org,
            created_at__date=today
        ).select_related('person', 'event').order_by('-created_at')[:10]

        stats = {
            'todays_events': todays_events.count(),
            'todays_bookings': todays_bookings.count(),
            'total_capacity_today': sum(event.capacity for event in todays_events),
            'total_bookings_today': sum(
                event.bookings.filter(status='confirmed').count()
                for event in todays_events
            )
        }

        context = {
            'stats': {'todays_events': todays_events.count()},
            'todays_events': todays_events,
            'dashboard_type': 'staff'
        }

        return render(request, 'core/dashboard_simple.html', context)

    except Exception as e:
        messages.error(request, f"Erro ao carregar dashboard: {str(e)}")
        return redirect('core:dashboard')


@login_required
def credit_history_view(request):
    """Vista para mostrar o histórico de créditos do cliente."""
    try:
        profile = request.user.profile
        if not hasattr(profile, 'person') or not profile.person:
            messages.error(request, "Perfil de cliente não encontrado.")
            return redirect('core:dashboard')

        person = profile.person
        org = request.organization

        # Histórico de reservas e pagamentos
        bookings_history = Booking.objects.filter(
            organization=org,
            person=person
        ).select_related(
            'event', 'event__resource', 'event__modality', 'event__instructor'
        ).order_by('-event__starts_at')

        # Subscrições históricas
        subscriptions_history = ClientSubscription.objects.filter(
            organization=org,
            person=person
        ).select_related('payment_plan').order_by('-created_at')

        # Resumo de créditos atual
        try:
            credit_summary = CreditHistoryService.get_client_credit_summary(person, org)
        except Exception:
            credit_summary = {'total_credits': 0, 'active_subscriptions': []}

        context = {
            'person': person,
            'bookings_history': bookings_history,
            'subscriptions_history': subscriptions_history,
            'credit_summary': credit_summary,
        }

        return render(request, 'core/credit_history.html', context)

    except Exception as e:
        messages.error(request, f"Erro ao carregar histórico: {str(e)}")
        return redirect('core:dashboard')


@login_required
def alert_mark_read(request, alert_id):
    """Marca um alerta como lido."""
    try:
        alert = get_object_or_404(SystemAlert, id=alert_id, organization=request.organization)

        # Verificar permissões básicas
        can_access = False
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            if (hasattr(profile, 'user_type') and
                profile.user_type in [UserProfile.UserType.ADMIN, UserProfile.UserType.STAFF]):
                can_access = True
            elif alert.person and hasattr(profile, 'person') and alert.person == profile.person:
                can_access = True
            elif alert.user and alert.user == request.user:
                can_access = True

        if can_access and hasattr(alert, 'mark_as_read'):
            alert.mark_as_read()
            messages.success(request, "Alerta marcado como lido.")
        else:
            messages.error(request, "Sem permissão para aceder a este alerta.")

    except Exception as e:
        messages.error(request, f"Erro ao processar alerta: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER', 'core:dashboard'))


@login_required
def alert_dismiss(request, alert_id):
    """Ignora um alerta."""
    try:
        alert = get_object_or_404(SystemAlert, id=alert_id, organization=request.organization)

        # Verificar permissões básicas (mesmo que mark_read)
        can_access = False
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            if (hasattr(profile, 'user_type') and
                profile.user_type in [UserProfile.UserType.ADMIN, UserProfile.UserType.STAFF]):
                can_access = True
            elif alert.person and hasattr(profile, 'person') and alert.person == profile.person:
                can_access = True
            elif alert.user and alert.user == request.user:
                can_access = True

        if can_access and hasattr(alert, 'dismiss'):
            alert.dismiss()
            messages.success(request, "Alerta ignorado.")
        else:
            messages.error(request, "Sem permissão para aceder a este alerta.")

    except Exception as e:
        messages.error(request, f"Erro ao processar alerta: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER', 'core:dashboard'))
