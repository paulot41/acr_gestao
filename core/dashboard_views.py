"""
Vistas específicas para dashboards personalizados por tipo de utilizador.
Dashboard simplificado para consulta e marcação de aulas - operações CRUD no Django Admin.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
import logging
from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist
from .models import (
    Person, Instructor, Event, Booking, ClientSubscription,
    SystemAlert, UserProfile, Modality, Resource, Payment, InstructorCommission
)
from .services.alerts import AlertService, CreditHistoryService

logger = logging.getLogger(__name__)


@login_required
def dashboard_router(request):
    """Dashboard unificado: redireciona para o Gantt para consulta/marcação de aulas."""
    return redirect('core:gantt')


@login_required
def admin_dashboard(request):
    """Dashboard de leitura amigável dos dados do admin"""
    org = getattr(request, 'organization', None)

    if not org:
        return render(request, 'core/dashboard/no_org.html')

    today = timezone.now().date()

    # Estatísticas gerais - usando campos corretos
    stats = {
        'total_clients': Person.objects.filter(organization=org).count(),
        'active_clients': Person.objects.filter(organization=org, status='active').count(),
        'total_instructors': Instructor.objects.filter(organization=org).count(),
        'active_instructors': Instructor.objects.filter(organization=org, is_active=True).count(),
        'total_modalities': Modality.objects.filter(organization=org).count(),
        'active_modalities': Modality.objects.filter(organization=org, is_active=True).count(),
    }

    # Eventos de hoje e próximos - usando campos corretos
    events_today = Event.objects.filter(
        organization=org,
        starts_at__date=today
    ).select_related('instructor', 'modality').order_by('starts_at')

    upcoming_events = Event.objects.filter(
        organization=org,
        starts_at__date__gt=today,
        starts_at__date__lte=today + timedelta(days=7)
    ).select_related('instructor', 'modality').order_by('starts_at')[:10]

    # Reservas recentes - usando relacionamento correto
    recent_bookings = Booking.objects.filter(
        event__organization=org
    ).select_related('event', 'person').order_by('-created_at')[:10]

    # Clientes com poucos créditos - usando relacionamento 'subscriptions'
    low_credits = Person.objects.filter(
        organization=org,
        status='active'
    ).annotate(
        total_credits=Sum('subscriptions__remaining_credits')
    ).filter(total_credits__lt=5).order_by('total_credits')[:10]

    context = {
        'organization': org,
        'stats': stats,
        'events_today': events_today,
        'upcoming_events': upcoming_events,
        'recent_bookings': recent_bookings,
        'low_credits': low_credits,
    }

    return render(request, 'core/dashboard/admin_dashboard.html', context)


@login_required
def clients_overview(request):
    """Vista de leitura dos clientes"""
    org = getattr(request, 'organization', None)
    if not org:
        return render(request, 'core/dashboard/no_org.html')

    clients = Person.objects.filter(organization=org).order_by('first_name', 'last_name')

    context = {
        'organization': org,
        'clients': clients,
        'total_clients': clients.count(),
        'active_clients': clients.filter(status='active').count(),
    }

    return render(request, 'core/dashboard/clients_overview.html', context)


@login_required
def instructors_overview(request):
    """Vista de leitura dos instrutores"""
    org = getattr(request, 'organization', None)
    if not org:
        return render(request, 'core/dashboard/no_org.html')

    instructors = Instructor.objects.filter(organization=org).annotate(
        total_events=Count('event'),
        events_this_month=Count('event', filter=Q(event__starts_at__month=timezone.now().month))
    ).order_by('first_name', 'last_name')

    context = {
        'organization': org,
        'instructors': instructors,
    }

    return render(request, 'core/dashboard/instructors_overview.html', context)


@login_required
def dashboard_admin(request):
    """Dashboard simplificado para administradores - consulta apenas."""
    org = request.organization

    # Executar verificações diárias de alertas
    try:
        AlertService.run_daily_checks(org)
    except DatabaseError as e:
        logger.error("Erro nos checks diários: %s", e)

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

    except DatabaseError as e:
        messages.error(request, f"Erro ao carregar dados: {str(e)}")
        logger.error("Erro ao carregar dados do dashboard admin: %s", e)
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

    except (ObjectDoesNotExist, DatabaseError) as e:
        messages.error(request, f"Erro ao carregar dashboard: {str(e)}")
        logger.error("Erro no dashboard do instrutor: %s", e)
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
        except DatabaseError as e:
            logger.error("Erro ao obter resumo de créditos: %s", e)
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

    except (ObjectDoesNotExist, DatabaseError) as e:
        messages.error(request, f"Erro ao carregar dashboard: {str(e)}")
        logger.error("Erro no dashboard do cliente: %s", e)
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

    except DatabaseError as e:
        messages.error(request, f"Erro ao carregar dashboard: {str(e)}")
        logger.error("Erro no dashboard do staff: %s", e)
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
        except DatabaseError as e:
            logger.error("Erro ao obter resumo de créditos: %s", e)
            credit_summary = {'total_credits': 0, 'active_subscriptions': []}

        context = {
            'person': person,
            'bookings_history': bookings_history,
            'subscriptions_history': subscriptions_history,
            'credit_summary': credit_summary,
        }

        return render(request, 'core/credit_history.html', context)

    except (ObjectDoesNotExist, DatabaseError) as e:
        messages.error(request, f"Erro ao carregar histórico: {str(e)}")
        logger.error("Erro ao carregar histórico de créditos: %s", e)
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

    except DatabaseError as e:
        messages.error(request, f"Erro ao processar alerta: {str(e)}")
        logger.error("Erro ao processar alerta: %s", e)

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

    except DatabaseError as e:
        messages.error(request, f"Erro ao processar alerta: {str(e)}")
        logger.error("Erro ao processar alerta: %s", e)

    return redirect(request.META.get('HTTP_REFERER', 'core:dashboard'))
