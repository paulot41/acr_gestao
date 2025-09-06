"""
Vistas específicas para dashboards personalizados por tipo de utilizador.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import timedelta, datetime
from .models import (
    Person, Instructor, Event, Booking, ClientSubscription
)
# Remove imports que não existem ainda
# from .services.alerts import AlertService, CreditHistoryService


@login_required
def dashboard_router(request):
    """Router que direciona para o dashboard apropriado baseado no tipo de utilizador."""
    try:
        profile = request.user.profile

        if profile.user_type == UserProfile.UserType.ADMIN:
            return redirect('dashboard_admin')
        elif profile.user_type == UserProfile.UserType.STAFF:
            return redirect('dashboard_staff')
        elif profile.user_type == UserProfile.UserType.INSTRUCTOR:
            return redirect('dashboard_instructor')
        elif profile.user_type == UserProfile.UserType.CLIENT:
            return redirect('dashboard_client')
        else:
            return redirect('dashboard_admin')  # Fallback

    except UserProfile.DoesNotExist:
        # Se não tem perfil, assume admin
        return redirect('dashboard_admin')


@login_required
def dashboard_admin(request):
    """Dashboard para administradores com visão completa."""
    org = request.organization

    # Executar verificações diárias de alertas
    AlertService.run_daily_checks(org)

    # Estatísticas gerais
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())

    stats = {
        'total_clients': Person.objects.filter(organization=org, status='active').count(),
        'total_instructors': Instructor.objects.filter(organization=org, is_active=True).count(),
        'active_subscriptions': ClientSubscription.objects.filter(
            organization=org, status='active'
        ).count(),
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

    # Alertas pendentes
    pending_alerts = SystemAlert.objects.filter(
        organization=org,
        status__in=[SystemAlert.Status.PENDING, SystemAlert.Status.SENT]
    ).order_by('-created_at')[:10]

    # Próximos eventos (hoje + amanhã)
    upcoming_events = Event.objects.filter(
        organization=org,
        starts_at__date__in=[today, today + timedelta(days=1)]
    ).select_related('resource', 'instructor', 'modality').order_by('starts_at')[:10]

    # Subscrições a expirar esta semana
    expiring_subscriptions = ClientSubscription.objects.filter(
        organization=org,
        status='active',
        end_date__lte=today + timedelta(days=7),
        end_date__gte=today
    ).select_related('person', 'payment_plan')[:5]

    # Clientes com créditos baixos
    low_credit_clients = ClientSubscription.objects.filter(
        organization=org,
        status='active',
        payment_plan__plan_type='credits',
        remaining_credits__lte=3,
        remaining_credits__gt=0
    ).select_related('person', 'payment_plan')[:5]

    context = {
        'stats': stats,
        'pending_alerts': pending_alerts,
        'upcoming_events': upcoming_events,
        'expiring_subscriptions': expiring_subscriptions,
        'low_credit_clients': low_credit_clients,
        'dashboard_type': 'admin'
    }

    return render(request, 'core/dashboard_admin.html', context)


@login_required
def dashboard_instructor(request):
    """Dashboard para instrutores com foco nas suas aulas."""
    try:
        profile = request.user.profile
        if not profile.instructor:
            messages.error(request, "Perfil de instrutor não encontrado.")
            return redirect('dashboard_router')

        instructor = profile.instructor
        org = request.organization
        today = timezone.now().date()

        # Próximas aulas do instrutor (próximos 7 dias)
        upcoming_classes = Event.objects.filter(
            organization=org,
            instructor=instructor,
            starts_at__date__gte=today,
            starts_at__date__lte=today + timedelta(days=7)
        ).select_related('resource', 'modality').order_by('starts_at')

        # Aulas de hoje
        todays_classes = Event.objects.filter(
            organization=org,
            instructor=instructor,
            starts_at__date=today
        ).select_related('resource', 'modality').order_by('starts_at')

        # Estatísticas do instrutor
        this_month_start = today.replace(day=1)
        stats = {
            'todays_classes': todays_classes.count(),
            'weekly_classes': upcoming_classes.count(),
            'monthly_classes': Event.objects.filter(
                organization=org,
                instructor=instructor,
                starts_at__date__gte=this_month_start
            ).count(),
            'total_students_today': sum(
                event.bookings.filter(status='confirmed').count()
                for event in todays_classes
            )
        }

        # Alertas para o instrutor
        instructor_alerts = SystemAlert.objects.filter(
            organization=org,
            user=request.user,
            status__in=[SystemAlert.Status.PENDING, SystemAlert.Status.SENT]
        ).order_by('-created_at')[:5]

        context = {
            'instructor': instructor,
            'stats': stats,
            'todays_classes': todays_classes,
            'upcoming_classes': upcoming_classes,
            'alerts': instructor_alerts,
            'dashboard_type': 'instructor'
        }

        return render(request, 'core/dashboard_instructor.html', context)

    except Exception as e:
        messages.error(request, f"Erro ao carregar dashboard: {str(e)}")
        return redirect('dashboard_router')


@login_required
def dashboard_client(request):
    """Dashboard para clientes com foco nas suas reservas e créditos."""
    try:
        profile = request.user.profile
        if not profile.person:
            messages.error(request, "Perfil de cliente não encontrado.")
            return redirect('dashboard_router')

        person = profile.person
        org = request.organization
        today = timezone.now().date()

        # Próximas reservas
        upcoming_bookings = Booking.objects.filter(
            organization=org,
            person=person,
            status='confirmed',
            event__starts_at__gte=timezone.now()
        ).select_related('event', 'event__resource', 'event__modality', 'event__instructor').order_by('event__starts_at')[:5]

        # Histórico de reservas (últimas 10)
        recent_bookings = Booking.objects.filter(
            organization=org,
            person=person
        ).select_related('event', 'event__resource', 'event__modality').order_by('-created_at')[:10]

        # Resumo de créditos
        credit_summary = CreditHistoryService.get_client_credit_summary(person, org)

        # Subscrições ativas
        active_subscriptions = ClientSubscription.objects.filter(
            organization=org,
            person=person,
            status='active'
        ).select_related('payment_plan')

        # Alertas pessoais
        personal_alerts = SystemAlert.objects.filter(
            organization=org,
            person=person,
            status__in=[SystemAlert.Status.PENDING, SystemAlert.Status.SENT]
        ).order_by('-created_at')[:5]

        # Estatísticas pessoais
        this_month_start = today.replace(day=1)
        stats = {
            'upcoming_bookings': upcoming_bookings.count(),
            'total_credits': credit_summary['total_credits'],
            'monthly_bookings': Booking.objects.filter(
                organization=org,
                person=person,
                event__starts_at__date__gte=this_month_start,
                status='confirmed'
            ).count(),
            'active_plans': active_subscriptions.count()
        }

        context = {
            'person': person,
            'stats': stats,
            'upcoming_bookings': upcoming_bookings,
            'recent_bookings': recent_bookings,
            'credit_summary': credit_summary,
            'active_subscriptions': active_subscriptions,
            'alerts': personal_alerts,
            'dashboard_type': 'client'
        }

        return render(request, 'core/dashboard_client.html', context)

    except Exception as e:
        messages.error(request, f"Erro ao carregar dashboard: {str(e)}")
        return redirect('dashboard_router')


@login_required
def dashboard_staff(request):
    """Dashboard para staff com foco em operações diárias."""
    org = request.organization
    today = timezone.now().date()

    # Eventos de hoje
    todays_events = Event.objects.filter(
        organization=org,
        starts_at__date=today
    ).select_related('resource', 'instructor', 'modality').order_by('starts_at')

    # Reservas pendentes ou recentes
    recent_bookings = Booking.objects.filter(
        organization=org,
        created_at__date=today
    ).select_related('person', 'event', 'event__resource').order_by('-created_at')[:10]

    # Pagamentos pendentes
    pending_payments = ClientSubscription.objects.filter(
        organization=org,
        is_paid=False,
        status='active'
    ).select_related('person', 'payment_plan')[:10]

    # Alertas operacionais
    operational_alerts = SystemAlert.objects.filter(
        organization=org,
        alert_type__in=[
            SystemAlert.AlertType.LOW_CREDITS,
            SystemAlert.AlertType.SUBSCRIPTION_EXPIRING,
            SystemAlert.AlertType.PAYMENT_OVERDUE
        ],
        status__in=[SystemAlert.Status.PENDING, SystemAlert.Status.SENT]
    ).order_by('-created_at')[:10]

    # Estatísticas do dia
    stats = {
        'todays_events': todays_events.count(),
        'todays_bookings': recent_bookings.count(),
        'pending_payments': pending_payments.count(),
        'active_alerts': operational_alerts.count(),
        'total_capacity_today': sum(event.capacity for event in todays_events),
        'total_bookings_today': sum(
            event.bookings.filter(status='confirmed').count()
            for event in todays_events
        )
    }

    context = {
        'stats': stats,
        'todays_events': todays_events,
        'recent_bookings': recent_bookings,
        'pending_payments': pending_payments,
        'alerts': operational_alerts,
        'dashboard_type': 'staff'
    }

    return render(request, 'core/dashboard_staff.html', context)


@login_required
def credit_history_view(request):
    """Vista para histórico detalhado de créditos (clientes)."""
    try:
        profile = request.user.profile
        if profile.user_type != UserProfile.UserType.CLIENT or not profile.person:
            messages.error(request, "Acesso negado.")
            return redirect('dashboard_router')

        person = profile.person
        org = request.organization

        credit_history = CreditHistory.objects.filter(
            organization=org,
            person=person
        ).select_related('subscription', 'booking', 'booking__event').order_by('-created_at')

        # Paginação simples
        page_size = 20
        page = int(request.GET.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size

        history_page = credit_history[start:end]
        has_next = credit_history.count() > end
        has_prev = page > 1

        context = {
            'credit_history': history_page,
            'page': page,
            'has_next': has_next,
            'has_prev': has_prev,
            'prev_page': page - 1 if has_prev else None,
            'next_page': page + 1 if has_next else None
        }

        return render(request, 'core/credit_history.html', context)

    except Exception as e:
        messages.error(request, f"Erro ao carregar histórico: {str(e)}")
        return redirect('dashboard_client')


@login_required
def alert_mark_read(request, alert_id):
    """Marca um alerta como lido."""
    alert = get_object_or_404(SystemAlert, id=alert_id, organization=request.organization)

    # Verificar permissões
    can_access = False
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
        if (profile.user_type in [UserProfile.UserType.ADMIN, UserProfile.UserType.STAFF] or
            (alert.person and alert.person == profile.person) or
            (alert.user and alert.user == request.user)):
            can_access = True

    if can_access:
        alert.mark_as_read()
        messages.success(request, "Alerta marcado como lido.")
    else:
        messages.error(request, "Sem permissão para aceder a este alerta.")

    return redirect(request.META.get('HTTP_REFERER', 'dashboard_router'))


@login_required
def alert_dismiss(request, alert_id):
    """Ignora um alerta."""
    alert = get_object_or_404(SystemAlert, id=alert_id, organization=request.organization)

    # Verificar permissões (mesmo que mark_read)
    can_access = False
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
        if (profile.user_type in [UserProfile.UserType.ADMIN, UserProfile.UserType.STAFF] or
            (alert.person and alert.person == profile.person) or
            (alert.user and alert.user == request.user)):
            can_access = True

    if can_access:
        alert.dismiss()
        messages.success(request, "Alerta ignorado.")
    else:
        messages.error(request, "Sem permissão para aceder a este alerta.")

    return redirect(request.META.get('HTTP_REFERER', 'dashboard_router'))
