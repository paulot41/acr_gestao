from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.views.decorators.http import require_http_methods
import json

from .models import (
    Person, Instructor, Modality, Event, Resource, Booking,
    Payment, Organization, InstructorCommission
)
from .forms import PersonForm, InstructorForm, ModalityForm, EventForm


@login_required
def admin_dashboard(request):
    """Interface admin integrada - página principal."""
    org = request.organization
    section = request.GET.get('section', 'dashboard')

    context = {
        'organization': org,
        'current_section': section,
        'sections': [
            {'id': 'dashboard', 'name': 'Dashboard', 'icon': 'speedometer2'},
            {'id': 'clients', 'name': 'Clientes', 'icon': 'people'},
            {'id': 'instructors', 'name': 'Instrutores', 'icon': 'person-badge'},
            {'id': 'modalities', 'name': 'Modalidades', 'icon': 'list-stars'},
            {'id': 'gantt', 'name': 'Gantt/Horários', 'icon': 'calendar-week'},
            {'id': 'payments', 'name': 'Pagamentos', 'icon': 'credit-card'},
            {'id': 'reports', 'name': 'Relatórios', 'icon': 'graph-up'},
            {'id': 'settings', 'name': 'Configurações', 'icon': 'gear'},
        ]
    }

    if section == 'dashboard':
        context.update(_get_dashboard_data(org))
    elif section == 'clients':
        context.update(_get_clients_data(request, org))
    elif section == 'instructors':
        context.update(_get_instructors_data(request, org))
    elif section == 'modalities':
        context.update(_get_modalities_data(request, org))
    elif section == 'gantt':
        context.update(_get_gantt_data(org))
    elif section == 'payments':
        context.update(_get_payments_data(request, org))
    elif section == 'settings':
        context.update(_get_settings_data(org))

    return render(request, 'core/admin_integrated.html', context)


def _get_dashboard_data(org):
    """Dados para a secção dashboard."""
    # Estatísticas gerais
    total_clients = Person.objects.filter(organization=org, status='active').count()
    acr_clients = Person.objects.filter(
        organization=org, status='active',
        entity_affiliation__in=['acr_only', 'both']
    ).count()
    proform_clients = Person.objects.filter(
        organization=org, status='active',
        entity_affiliation__in=['proform_only', 'both']
    ).count()

    total_instructors = Instructor.objects.filter(organization=org, is_active=True).count()
    total_modalities = Modality.objects.filter(organization=org, is_active=True).count()

    # Próximas aulas (próximas 24h)
    tomorrow = timezone.now() + timedelta(days=1)
    upcoming_events = Event.objects.filter(
        organization=org,
        starts_at__gte=timezone.now(),
        starts_at__lte=tomorrow
    ).order_by('starts_at')[:5]

    # Receitas do mês atual
    current_month = timezone.now().replace(day=1)
    monthly_revenue = Payment.objects.filter(
        organization=org,
        status='completed',
        paid_date__gte=current_month
    ).aggregate(total=Count('amount'))['total'] or 0

    return {
        'total_clients': total_clients,
        'acr_clients': acr_clients,
        'proform_clients': proform_clients,
        'total_instructors': total_instructors,
        'total_modalities': total_modalities,
        'upcoming_events': upcoming_events,
        'monthly_revenue': monthly_revenue,
    }


def _get_clients_data(request, org):
    """Dados para a secção clientes."""
    clients = Person.objects.filter(organization=org)

    # Filtros
    search = request.GET.get('search')
    status_filter = request.GET.get('status')
    entity_filter = request.GET.get('entity')

    if search:
        clients = clients.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    if status_filter:
        clients = clients.filter(status=status_filter)

    if entity_filter:
        clients = clients.filter(entity_affiliation=entity_filter)

    # Paginação
    paginator = Paginator(clients, 10)  # Menor para o admin integrado
    page_number = request.GET.get('page')
    clients = paginator.get_page(page_number)

    return {
        'clients': clients,
        'search': search,
        'status_filter': status_filter,
        'entity_filter': entity_filter,
        'status_choices': Person.Status.choices,
        'entity_choices': Person.EntityAffiliation.choices,
        'client_form': PersonForm(),
    }


def _get_instructors_data(request, org):
    """Dados para a secção instrutores."""
    instructors = Instructor.objects.filter(organization=org)

    search = request.GET.get('search')
    entity_filter = request.GET.get('entity')

    if search:
        instructors = instructors.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    if entity_filter:
        instructors = instructors.filter(entity_affiliation=entity_filter)

    paginator = Paginator(instructors, 10)
    page_number = request.GET.get('page')
    instructors = paginator.get_page(page_number)

    return {
        'instructors': instructors,
        'search': search,
        'entity_filter': entity_filter,
        'entity_choices': Instructor.EntityAffiliation.choices,
        'instructor_form': InstructorForm(),
    }


def _get_modalities_data(request, org):
    """Dados para a secção modalidades."""
    modalities = Modality.objects.filter(organization=org)

    entity_filter = request.GET.get('entity')
    if entity_filter:
        modalities = modalities.filter(entity_type=entity_filter)

    return {
        'modalities': modalities,
        'entity_filter': entity_filter,
        'entity_choices': Modality.EntityType.choices,
        'modality_form': ModalityForm(),
    }


def _get_gantt_data(org):
    """Dados para a secção gantt."""
    resources = Resource.objects.filter(organization=org)
    instructors = Instructor.objects.filter(organization=org, is_active=True)
    modalities = Modality.objects.filter(organization=org, is_active=True)

    return {
        'resources': resources,
        'instructors': instructors,
        'modalities': modalities,
    }


def _get_payments_data(request, org):
    """Dados para a secção pagamentos."""
    payments = Payment.objects.filter(organization=org).select_related('person')

    status_filter = request.GET.get('status')
    if status_filter:
        payments = payments.filter(status=status_filter)

    paginator = Paginator(payments, 10)
    page_number = request.GET.get('page')
    payments = paginator.get_page(page_number)

    return {
        'payments': payments,
        'status_filter': status_filter,
        'status_choices': Payment.Status.choices,
    }


def _get_settings_data(org):
    """Dados para a secção configurações."""
    return {
        'gym_monthly_fee': org.gym_monthly_fee,
        'wellness_monthly_fee': org.wellness_monthly_fee,
        'org_type': org.org_type,
    }


# APIs para operações AJAX
@login_required
@require_http_methods(["POST"])
def admin_create_client(request):
    """API para criar cliente via AJAX."""
    form = PersonForm(request.POST, request.FILES)
    if form.is_valid():
        client = form.save(commit=False)
        client.organization = request.organization
        client.save()
        return JsonResponse({
            'success': True,
            'message': f'Cliente {client.full_name} criado com sucesso!',
            'redirect': f'/admin/?section=clients'
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })


@login_required
@require_http_methods(["POST"])
def admin_create_instructor(request):
    """API para criar instrutor via AJAX."""
    form = InstructorForm(request.POST, request.FILES)
    if form.is_valid():
        instructor = form.save(commit=False)
        instructor.organization = request.organization
        instructor.save()
        return JsonResponse({
            'success': True,
            'message': f'Instrutor {instructor.full_name} criado com sucesso!',
            'redirect': f'/admin/?section=instructors'
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })


@login_required
@require_http_methods(["POST"])
def admin_create_modality(request):
    """API para criar modalidade via AJAX."""
    form = ModalityForm(request.POST)
    if form.is_valid():
        modality = form.save(commit=False)
        modality.organization = request.organization
        modality.save()
        return JsonResponse({
            'success': True,
            'message': f'Modalidade {modality.name} criada com sucesso!',
            'redirect': f'/admin/?section=modalities'
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })


@login_required
def admin_events_json(request):
    """API endpoint para eventos do calendário/gantt no admin."""
    org = request.organization
    start = request.GET.get('start')
    end = request.GET.get('end')

    events = Event.objects.filter(organization=org)

    if start:
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
        events = events.filter(starts_at__gte=start_date)

    if end:
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
        events = events.filter(ends_at__lte=end_date)

    events_data = []
    for event in events:
        # Determinar cor baseada no espaço
        color = '#0d6efd'  # Azul padrão
        if event.resource.name == 'Sala de Pilates':
            color = '#198754'  # Verde
        elif event.resource.name == 'Pavilhão':
            color = '#ffc107'  # Amarelo

        events_data.append({
            'id': event.id,
            'title': event.title,
            'start': event.starts_at.isoformat(),
            'end': event.ends_at.isoformat(),
            'resourceId': event.resource.id,
            'backgroundColor': color,
            'borderColor': color,
        })

    return JsonResponse(events_data, safe=False)
