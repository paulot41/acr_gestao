import csv
from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from .auth_views import role_required, acr_required, proform_required, protocol_access_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError, IntegrityError
from django.db.models import Q, Count, Sum
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from .models import (
    Person, Instructor, Modality, Event, Resource, Payment, Booking,
    PaymentPlan, ClientSubscription, CreditHistory, GoogleDriveSyncLog,
    InstructorCommission, ProtocolPeriodSettlement, ProtocolConfiguration,
    AthleteGraduation, GoverningBody, GoverningBodyMember
)
from notifications.models import NotificationLog
from .forms import (
    PersonForm, InstructorForm, ModalityForm, EventForm, BookingForm, ResourceForm,
    PaymentRegistrationForm, ClientSubscriptionForm, ProtocolConfigurationForm
)
from .services.communications import send_athlete_welcome_email, get_whatsapp_url
from .services.protocol_finance import calculate_period_protocol_split, create_or_update_period_settlement
from .services.membership_card import get_membership_card_data
from .services.kiosk import resolve_person, get_active_event_for_facility, process_kiosk_checkin



@role_required(["admin", "staff"])
def dashboard(request):
    """Dashboard principal moderno com KPIs e gráficos interativos."""
    org = request.organization

    # Estatísticas detalhadas por entidade
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
    acr_instructors = Instructor.objects.filter(
        organization=org, is_active=True,
        entity_affiliation__in=['acr_only', 'both']
    ).count()
    proform_instructors = Instructor.objects.filter(
        organization=org, is_active=True,
        entity_affiliation__in=['proform_only', 'both']
    ).count()

    total_modalities = Modality.objects.filter(organization=org, is_active=True).count()
    acr_modalities = Modality.objects.filter(
        organization=org, is_active=True,
        entity_type__in=['acr', 'both']
    ).count()
    proform_modalities = Modality.objects.filter(
        organization=org, is_active=True,
        entity_type__in=['proform', 'both']
    ).count()

    # Próximas aulas (próximas 24h)
    tomorrow = timezone.now() + timedelta(days=1)
    upcoming_events = Event.objects.filter(
        organization=org,
        starts_at__gte=timezone.now(),
        starts_at__lte=tomorrow
    ).select_related('resource', 'modality', 'instructor').order_by('starts_at')[:5]

    # Receitas do mês atual (corrigido)
    current_month = timezone.now().replace(day=1)
    monthly_payments = Payment.objects.filter(
        organization=org,
        status=Payment.Status.COMPLETED,
        paid_date__gte=current_month
    )
    monthly_revenue = sum(payment.amount for payment in monthly_payments)

    # Clientes recentes (últimos 7 dias)
    week_ago = timezone.now() - timedelta(days=7)
    recent_clients = Person.objects.filter(
        organization=org,
        created_at__gte=week_ago
    ).order_by('-created_at')[:6]  # Aumentado para 6 para melhor layout

    context = {
        # Estatísticas gerais
        'total_clients': total_clients,
        'acr_clients': acr_clients,
        'proform_clients': proform_clients,
        'total_instructors': total_instructors,
        'acr_instructors': acr_instructors,
        'proform_instructors': proform_instructors,
        'total_modalities': total_modalities,
        'acr_modalities': acr_modalities,
        'proform_modalities': proform_modalities,

        # Dados dinâmicos
        'upcoming_events': upcoming_events,
        'monthly_revenue': monthly_revenue,
        'recent_clients': recent_clients,

        # Configurações da organização
        'organization': org,
    }
    return render(request, 'core/dashboard_main.html', context)


# CLIENTES VIEWS
@role_required(["admin", "staff"])
def client_list(request):
    """Listagem de clientes com filtros e paginação."""
    org = request.organization
    clients = Person.objects.filter(organization=org).order_by('first_name', 'last_name')

    # Filtros
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    entity = request.GET.get('entity', '').strip()
    member_category = request.GET.get('member_category', '').strip()
    fee_status = request.GET.get('membership_fee_status', '').strip()

    if search:
        clients = clients.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(nif__icontains=search)
        )

    if status_filter:
        clients = clients.filter(status=status_filter)

    if entity:
        if entity in ('acr', 'acr_only'):
            clients = clients.filter(entity_affiliation__in=[Person.EntityAffiliation.ACR_ONLY, Person.EntityAffiliation.BOTH])
        elif entity in ('proform', 'proform_only'):
            clients = clients.filter(entity_affiliation__in=[Person.EntityAffiliation.PROFORM_ONLY, Person.EntityAffiliation.BOTH])
        elif entity == 'both':
            clients = clients.filter(entity_affiliation=Person.EntityAffiliation.BOTH)
        else:
            clients = clients.filter(entity_affiliation=entity)

    if member_category:
        clients = clients.filter(member_category=member_category)

    if fee_status:
        clients = clients.filter(membership_fee_status=fee_status)

    # Paginação
    paginator = Paginator(clients, 25)
    page_number = request.GET.get('page')
    clients_page = paginator.get_page(page_number)

    created = request.GET.get('created') == '1'
    created_client = None
    created_client_id = request.GET.get('client_id')
    if created and created_client_id and created_client_id.isdigit():
        created_client = Person.objects.filter(
            organization=org, pk=int(created_client_id)
        ).first()

    context = {
        'clients': clients_page,
        'search': search,
        'status_filter': status_filter,
        'status': status_filter,
        'entity': entity,
        'member_category': member_category,
        'fee_status': fee_status,
        'status_choices': Person.Status.choices,
        'member_category_choices': Person.MemberCategory.choices,
        'fee_status_choices': Person.MembershipFeeStatus.choices,
        'created': created,
        'created_client': created_client,
    }
    return render(request, 'core/client_list.html', context)


@role_required(["admin", "staff"])
def client_detail(request, pk):
    """Ficha 360º do cliente/atleta com seguros, subscrições e histórico financeiro."""
    org = request.organization
    client = get_object_or_404(Person, pk=pk, organization=org)
    subscriptions = client.subscriptions.select_related('payment_plan').order_by('-start_date')
    active_sub = client.active_subscription
    recent_bookings = client.bookings.select_related('event', 'event__modality', 'event__resource').order_by('-created_at')[:10]
    recent_payments = client.payments.order_by('-paid_date', '-created_at')[:10]
    credit_history = client.credit_history.order_by('-created_at')[:10]

    # Graduações e Exames de Cinto
    graduations = client.graduations.select_related('modality', 'examiner').order_by('-awarded_date')
    modalities = Modality.objects.filter(organization=org, is_active=True)
    instructors = Instructor.objects.filter(organization=org, is_active=True)

    # Comunicações e WhatsApp
    recent_notifications = NotificationLog.objects.filter(person=client).order_by('-sent_at', '-id')[:5]
    whatsapp_welcome = get_whatsapp_url(client, 'welcome')
    whatsapp_insurance = get_whatsapp_url(client, 'insurance')
    whatsapp_payment = get_whatsapp_url(client, 'payment')
    whatsapp_schedule = get_whatsapp_url(client, 'schedule')

    context = {
        'client': client,
        'subscriptions': subscriptions,
        'active_sub': active_sub,
        'recent_bookings': recent_bookings,
        'recent_payments': recent_payments,
        'credit_history': credit_history,
        'insurance_status': client.insurance_status,
        'medical_status': client.medical_status,
        'is_minor': client.is_minor,
        'graduations': graduations,
        'modalities': modalities,
        'instructors': instructors,
        'recent_notifications': recent_notifications,
        'whatsapp_welcome': whatsapp_welcome,
        'whatsapp_insurance': whatsapp_insurance,
        'whatsapp_payment': whatsapp_payment,
        'whatsapp_schedule': whatsapp_schedule,
    }
    return render(request, 'core/client_detail.html', context)


@role_required(["admin", "staff"])
def client_create(request):
    """Criar novo cliente/atleta."""
    org = request.organization
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, organization=org, user=request.user)
        if form.is_valid():
            client = form.save(commit=False)
            client.organization = org
            client.save()

            # Disparar e-mail de boas-vindas com apólice de seguro se tiver e-mail
            if client.email:
                welcome_sent = send_athlete_welcome_email(client, request)
                if welcome_sent:
                    messages.success(request, f'Atleta {client.full_name} registado com sucesso! E-mail de boas-vindas com dados da apólice enviado para {client.email}.')
                else:
                    messages.success(request, f'Atleta {client.full_name} registado com sucesso!')
            else:
                messages.success(request, f'Atleta {client.full_name} registado com sucesso!')

            return redirect('core:client_detail', pk=client.pk)
    else:
        form = PersonForm(organization=org, user=request.user)

    return render(request, 'core/client_form.html', {'form': form, 'title': 'Novo Atleta / Cliente'})


@role_required(["admin", "staff"])
def client_edit(request, pk):
    """Editar atleta/cliente existente."""
    org = request.organization
    client = get_object_or_404(Person, pk=pk, organization=org)

    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, instance=client, organization=org, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Ficha de {client.full_name} atualizada com sucesso!')
            return redirect('core:client_detail', pk=client.pk)
    else:
        form = PersonForm(instance=client, organization=org, user=request.user)

    return render(request, 'core/client_form.html', {
        'form': form,
        'client': client,
        'title': f'Editar Atleta: {client.full_name}'
    })


@role_required(["admin", "staff"])
def client_add(request):
    """Adicionar novo cliente."""
    org = request.organization

    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, organization=org, user=request.user)
        if form.is_valid():
            client = form.save(commit=False)
            client.organization = org
            client.save()

            if client.email:
                welcome_sent = send_athlete_welcome_email(client, request)
                if welcome_sent:
                    messages.success(request, f'Atleta {client.full_name} registado com sucesso! E-mail de boas-vindas com dados da apólice enviado para {client.email}.')
                else:
                    messages.success(request, f'Atleta {client.full_name} registado com sucesso!')
            else:
                messages.success(request, f'Atleta {client.full_name} registado com sucesso!')

            return redirect('core:client_detail', pk=client.pk)
    else:
        form = PersonForm(organization=org, user=request.user)

    return render(request, 'core/client_form.html', {
        'form': form,
        'title': 'Adicionar Cliente',
        'action': 'add'
    })

@role_required(["admin", "staff"])
@require_http_methods(["POST"])
def client_delete(request, pk):
    """Eliminar cliente."""
    client = get_object_or_404(Person, pk=pk, organization=request.organization)

    try:
        client.delete()
        messages.success(request, f'Cliente {client.full_name} eliminado com sucesso!')
    except ProtectedError:
        messages.error(request, 'Não é possível eliminar este cliente porque existem faturas associadas.')
    except DatabaseError:
        messages.error(request, 'Não foi possível eliminar o cliente. Tente novamente.')

    return redirect('core:client_list')


# INSTRUTORES VIEWS
@role_required(["admin", "staff"])
def instructor_list(request):
    """Listagem de instrutores."""
    org = request.organization
    instructors = Instructor.objects.filter(organization=org, is_active=True).order_by('first_name', 'last_name')

    search = request.GET.get('search', '').strip()
    if search:
        instructors = instructors.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    context = {'instructors': instructors, 'search': search}
    return render(request, 'core/instructor_list.html', context)


@role_required(["admin", "staff"])
def instructor_detail(request, pk):
    """Detalhes de um instrutor específico."""
    instructor = get_object_or_404(Instructor, pk=pk, organization=request.organization)

    # Próximas aulas do instrutor (próximos 7 dias)
    next_week = timezone.now() + timedelta(days=7)
    upcoming_events = Event.objects.filter(
        organization=request.organization,
        instructor=instructor,
        starts_at__gte=timezone.now(),
        starts_at__lte=next_week
    ).order_by('starts_at')[:10]

    # Ganhos do mês (simulado por agora)
    monthly_earnings = 500  # Seria calculado baseado nas comissões reais

    context = {
        'instructor': instructor,
        'upcoming_events': upcoming_events,
        'monthly_earnings': monthly_earnings,
        'now': timezone.now(),
    }
    return render(request, 'core/instructor_detail.html', context)


@role_required(["admin", "staff"])
def instructor_create(request):
    """Criar novo instrutor."""
    if request.method == 'POST':
        form = InstructorForm(request.POST, request.FILES, organization=request.organization)
        if form.is_valid():
            instructor = form.save(commit=False)
            instructor.organization = request.organization
            instructor.save()
            messages.success(request, f'Instrutor {instructor.full_name} criado com sucesso!')
            return redirect('instructor_list')
    else:
        form = InstructorForm(organization=request.organization)

    return render(request, 'core/instructor_form.html', {'form': form, 'title': 'Novo Instrutor'})


@role_required(["admin", "staff"])
def instructor_edit(request, pk):
    """Editar instrutor existente."""
    instructor = get_object_or_404(Instructor, pk=pk, organization=request.organization)

    if request.method == 'POST':
        form = InstructorForm(request.POST, request.FILES, instance=instructor, organization=request.organization)
        if form.is_valid():
            form.save()
            messages.success(request, f'Instrutor {instructor.full_name} atualizado com sucesso!')
            return redirect('core:instructor_detail', pk=instructor.pk)
    else:
        form = InstructorForm(instance=instructor, organization=request.organization)

    return render(request, 'core/instructor_form.html', {
        'form': form,
        'instructor': instructor,
        'title': 'Editar Instrutor'
    })


@role_required(["admin", "staff"])
def instructor_add(request):
    """Adicionar novo instrutor."""
    org = request.organization

    if request.method == 'POST':
        form = InstructorForm(request.POST, request.FILES, organization=org)
        if form.is_valid():
            instructor = form.save(commit=False)
            instructor.organization = org
            instructor.save()
            messages.success(request, f'Instrutor {instructor.full_name} criado com sucesso!')
            return redirect('core:instructor_detail', pk=instructor.pk)
    else:
        form = InstructorForm(organization=org)

    return render(request, 'core/instructor_form.html', {
        'form': form,
        'title': 'Adicionar Instrutor',
        'action': 'add'
    })


# MODALIDADES VIEWS
@role_required(["admin", "staff"])
def modality_list(request):
    """Listagem de modalidades."""
    org = request.organization
    modalities = Modality.objects.filter(organization=org, is_active=True).order_by('entity_type', 'name')

    context = {'modalities': modalities}
    return render(request, 'core/modality_list.html', context)


@role_required(["admin", "staff"])
def modality_create(request):
    """Criar nova modalidade."""
    if request.method == 'POST':
        form = ModalityForm(request.POST, organization=request.organization)
        if form.is_valid():
            modality = form.save(commit=False)
            modality.organization = request.organization
            try:
                modality.save()
                messages.success(request, f'Modalidade {modality.name} criada com sucesso!')
                return redirect('core:modality_list')
            except IntegrityError:
                form.add_error('name', 'Já existe uma modalidade com este nome.')
    else:
        form = ModalityForm(organization=request.organization)

    return render(request, 'core/modality_form.html', {'form': form, 'title': 'Nova Modalidade'})


@role_required(["admin", "staff"])
def modality_edit(request, pk):
    """Editar modalidade existente."""
    modality = get_object_or_404(Modality, pk=pk, organization=request.organization)

    if request.method == 'POST':
        form = ModalityForm(request.POST, instance=modality, organization=request.organization)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Modalidade {modality.name} atualizada com sucesso!')
                return redirect('core:modality_list')
            except IntegrityError:
                form.add_error('name', 'Já existe uma modalidade com este nome.')
    else:
        form = ModalityForm(instance=modality, organization=request.organization)

    return render(request, 'core/modality_form.html', {
        'form': form,
        'modality': modality,
        'title': 'Editar Modalidade'
    })


@role_required(["admin", "staff"])
def modality_add(request):
    """Adicionar nova modalidade."""
    org = request.organization

    if request.method == 'POST':
        form = ModalityForm(request.POST, organization=org)
        if form.is_valid():
            modality = form.save(commit=False)
            modality.organization = org
            try:
                modality.save()
                messages.success(request, f'Modalidade {modality.name} criada com sucesso!')
                return redirect('core:modality_list')
            except IntegrityError:
                form.add_error('name', 'Já existe uma modalidade com este nome.')
    else:
        form = ModalityForm(organization=org)

    return render(request, 'core/modality_form.html', {
        'form': form,
        'title': 'Adicionar Modalidade',
        'action': 'add'
    })


# ESPAÇOS (RESOURCES) VIEWS
@role_required(["admin", "staff"])
def resource_list(request):
    """Listagem de espaços/recursos."""
    org = request.organization
    resources = Resource.objects.filter(organization=org).order_by('name')

    context = {
        'resources': resources,
    }
    return render(request, 'core/resource_list.html', context)


@role_required(["admin", "staff"])
def resource_add(request):
    """Adicionar novo espaço/recurso."""
    org = request.organization

    if request.method == 'POST':
        form = ResourceForm(request.POST, organization=org)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.organization = org
            try:
                resource.save()
                messages.success(request, f'Espaço "{resource.name}" criado com sucesso!')
                return redirect('core:resource_list')
            except IntegrityError:
                form.add_error('name', 'Já existe um espaço com este nome.')
    else:
        form = ResourceForm(organization=org)

    return render(request, 'core/resource_form.html', {
        'form': form,
        'title': 'Adicionar Espaço',
        'action': 'add'
    })


@role_required(["admin", "staff"])
def resource_edit(request, pk):
    """Editar espaço/recurso existente."""
    org = request.organization
    resource = get_object_or_404(Resource, pk=pk, organization=org)

    if request.method == 'POST':
        form = ResourceForm(request.POST, instance=resource, organization=org)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Espaço "{resource.name}" atualizado com sucesso!')
                return redirect('core:resource_list')
            except IntegrityError:
                form.add_error('name', 'Já existe um espaço com este nome.')
    else:
        form = ResourceForm(instance=resource, organization=org)

    return render(request, 'core/resource_form.html', {
        'form': form,
        'resource': resource,
        'title': 'Editar Espaço',
        'action': 'edit'
    })


# GANTT E EVENTOS
@role_required(["admin", "staff", "instructor"])
def gantt_system(request):
    """Redirecionar para a vista moderna e unificada do Gantt."""
    return redirect('core:gantt')


@role_required(["admin", "staff", "instructor"])
def gantt_view(request):
    """Redirecionar para a vista moderna e unificada do Gantt."""
    return redirect('core:gantt')


@role_required(["admin", "staff", "instructor"])
def events_json(request):
    """API endpoint OTIMIZADA para eventos do calendário/gantt."""
    org = request.organization
    start = request.GET.get('start')
    end = request.GET.get('end')

    # Otimização: aplicar filtros diretamente no QuerySet com select_related
    events = Event.objects.filter(organization=org).select_related(
        'resource', 'modality', 'instructor'
    )

    # Otimização: filtros de data aplicados ao QuerySet, não em Python
    if start:
        try:
            start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
            events = events.filter(starts_at__gte=start_date)
        except ValueError:
            pass

    if end:
        try:
            end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
            events = events.filter(ends_at__lte=end_date)
        except ValueError:
            pass

    # OTIMIZAÇÃO ADICIONAL: Filtros por instrutor e modalidade
    instructor_filter = request.GET.get('instructor')
    if instructor_filter:
        events = events.filter(instructor_id=instructor_filter)

    modality_filter = request.GET.get('modality')
    if modality_filter:
        events = events.filter(modality_id=modality_filter)

    # OTIMIZAÇÃO ADICIONAL: Filtro por recursos
    resources_filter = request.GET.get('resources')
    if resources_filter:
        resource_ids = resources_filter.split(',')
        events = events.filter(resource_id__in=resource_ids)

    # Otimização: usar only() para carregar apenas campos necessários
    events = events.only(
        'id', 'title', 'starts_at', 'ends_at', 'capacity',
        'resource__id', 'resource__name',
        'modality__color', 'modality__name',
        'instructor__first_name', 'instructor__last_name'
    ).order_by('starts_at')

    # OTIMIZAÇÃO: Limitar resultados para evitar sobrecarga
    events = events[:1000]  # Máximo 1000 eventos por request

    # Otimização: construir JSON de forma mais eficiente
    events_data = []
    for event in events:
        # Determinar cor baseada na modalidade ou usar padrão
        color = getattr(event.modality, 'color', '#0d6efd') if event.modality else '#0d6efd'

        # Construir título mais informativo
        title = event.title
        if event.instructor:
            title += f' - {event.instructor.first_name}'

        events_data.append({
            'id': event.id,
            'title': title,
            'start': event.starts_at.isoformat(),
            'end': event.ends_at.isoformat(),
            'resourceId': str(event.resource_id),  # Usar FK diretamente
            'backgroundColor': color,
            'borderColor': color,
            'textColor': '#ffffff' if color != '#ffffff' else '#000000',
            'extendedProps': {
                'capacity': event.capacity,
                'instructorId': event.instructor_id,
                'modalityId': event.modality_id,
                'resourceName': getattr(event.resource, 'name', ''),
            }
        })

    # OTIMIZAÇÃO: Headers de cache para melhor performance
    from django.http import JsonResponse
    response = JsonResponse(events_data, safe=False)
    response['Cache-Control'] = 'public, max-age=60'  # Cache por 1 minuto
    return response


@role_required(["admin", "staff"])
def event_create(request):
    """Criar novo evento/aula."""
    if request.method == 'POST':
        form = EventForm(request.POST, organization=request.organization)
        if form.is_valid():
            event = form.save(commit=False)
            event.organization = request.organization
            try:
                event.save()
                messages.success(request, f'Aula {event.title} criada com sucesso!')
                return redirect('core:gantt')
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = EventForm(organization=request.organization)

    return render(request, 'core/event_form.html', {'form': form, 'title': 'Nova Aula'})


@role_required(["admin", "staff"])
def event_list(request):
    """Listagem de eventos/aulas."""
    org = request.organization

    # Base queryset
    events_qs = Event.objects.filter(organization=org).select_related(
        'resource', 'modality', 'instructor'
    ).annotate(
        active_bookings_count=Count('bookings', filter=Q(bookings__status=Booking.Status.CONFIRMED))
    ).order_by('-starts_at')

    # Filtros (opcional)
    search = request.GET.get('search') or ''
    modality_filter = request.GET.get('modality') or ''
    instructor_filter = request.GET.get('instructor') or ''
    resource_filter = request.GET.get('resource') or ''
    period_filter = request.GET.get('period') or 'all'

    if search:
        events_qs = events_qs.filter(title__icontains=search)
    if modality_filter:
        events_qs = events_qs.filter(modality_id=modality_filter)
    if instructor_filter:
        events_qs = events_qs.filter(instructor_id=instructor_filter)
    if resource_filter:
        events_qs = events_qs.filter(resource_id=resource_filter)
    if period_filter == 'today':
        events_qs = events_qs.filter(starts_at__date=timezone.now().date())
    elif period_filter == 'week':
        start = timezone.now().date()
        end = start + timedelta(days=7)
        events_qs = events_qs.filter(starts_at__date__gte=start, starts_at__date__lte=end)
    elif period_filter == 'month':
        start = timezone.now().date().replace(day=1)
        events_qs = events_qs.filter(starts_at__date__gte=start)
    elif period_filter == 'upcoming':
        events_qs = events_qs.filter(starts_at__gte=timezone.now())

    export = request.GET.get('export')
    if export == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=eventos.csv'
        writer = csv.writer(response)
        writer.writerow([
            'Data Inicio', 'Hora Inicio', 'Hora Fim', 'Titulo', 'Modalidade',
            'Instrutor', 'Espaco', 'Capacidade', 'Reservas', 'Estado'
        ])
        now = timezone.now()
        for ev in events_qs.iterator():
            if ev.starts_at > now:
                status_label = 'Agendada'
            elif ev.ends_at < now:
                status_label = 'Concluida'
            else:
                status_label = 'A decorrer'
            writer.writerow([
                ev.starts_at.strftime('%Y-%m-%d'),
                ev.starts_at.strftime('%H:%M'),
                ev.ends_at.strftime('%H:%M'),
                ev.title,
                ev.modality.name if ev.modality else '',
                ev.instructor.full_name if ev.instructor else '',
                ev.resource.name if ev.resource else '',
                ev.capacity,
                ev.active_bookings_count,
                status_label,
            ])
        return response

    # Paginação
    paginator = Paginator(events_qs, 20)
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)

    # Enriquecer eventos com classes de ocupação para o template
    for ev in events:
        booked = getattr(ev, 'active_bookings_count', None)
        if booked is None:
            booked = ev.bookings.exclude(status=Booking.Status.CANCELLED).count()
        capacity = ev.capacity or 0
        ratio = (booked / capacity) if capacity else 0
        if ratio >= 1:
            ev.occupancy_class = 'bg-danger'
        elif ratio >= 0.8:
            ev.occupancy_class = 'bg-warning'
        else:
            ev.occupancy_class = 'bg-success'

    # Dados auxiliares para filtros e métricas rápidas
    modalities = Modality.objects.filter(organization=org).order_by('name')
    instructors = Instructor.objects.filter(organization=org, is_active=True).order_by('first_name', 'last_name')
    resources = Resource.objects.filter(organization=org).order_by('name')

    context = {
        'events': events,
        'modalities': modalities,
        'instructors': instructors,
        'resources': resources,
        'search': search,
        'modality_filter': str(modality_filter),
        'instructor_filter': str(instructor_filter),
        'resource_filter': str(resource_filter),
        'period_filter': period_filter,
        'now': timezone.now(),
        'total_events': Event.objects.filter(organization=org).count(),
        'today_events': Event.objects.filter(organization=org, starts_at__date=timezone.now().date()).count(),
        'upcoming_events_count': Event.objects.filter(organization=org, starts_at__gte=timezone.now()).count(),
    }

    return render(request, 'core/event_list.html', context)


@role_required(["admin", "staff"])
def event_edit(request, pk):
    """Editar evento/aula existente."""
    event = get_object_or_404(Event, pk=pk, organization=request.organization)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, organization=request.organization)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Aula {event.title} atualizada com sucesso!')
                return redirect('core:event_list')
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = EventForm(instance=event, organization=request.organization)

    return render(request, 'core/event_form.html', {
        'form': form,
        'event': event,
        'title': 'Editar Aula'
    })


@role_required(["admin", "staff"])
def event_add(request):
    """Adicionar novo evento."""
    org = request.organization

    if request.method == 'POST':
        form = EventForm(request.POST, organization=org)
        if form.is_valid():
            event = form.save(commit=False)
            event.organization = org
            try:
                event.save()
                messages.success(request, f'Evento {event.title} criado com sucesso!')
                return redirect('core:schedule')
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = EventForm(organization=org)

    return render(request, 'core/event_form.html', {
        'form': form,
        'title': 'Adicionar Evento',
        'action': 'add'
    })


@role_required(["admin", "staff"])
def event_delete(request, pk):
    """Eliminar evento."""
    org = request.organization
    event = get_object_or_404(Event, pk=pk, organization=org)

    if request.method == 'POST':
        title = event.title
        try:
            event.delete()
            messages.success(request, f'Evento "{title}" eliminado com sucesso!')
            return redirect('core:schedule')
        except (ProtectedError, DatabaseError) as e:
            messages.error(request, f'Não é possível eliminar o evento "{title}": existem registos associados.')
            return redirect('core:schedule')

    return render(request, 'core/event_confirm_delete.html', {
        'event': event
    })


@role_required(["admin", "staff"])
def booking_list(request):
    """Listagem de reservas."""
    org = request.organization
    bookings = Booking.objects.filter(organization=org).select_related("event", "person").order_by('-created_at')

    search = (request.GET.get('search') or '').strip()
    status_filter = request.GET.get('status') or ''
    start_date_raw = request.GET.get('start_date') or ''
    end_date_raw = request.GET.get('end_date') or ''
    start_date = parse_date(start_date_raw) if start_date_raw else None
    end_date = parse_date(end_date_raw) if end_date_raw else None

    if search:
        bookings = bookings.filter(
            Q(person__first_name__icontains=search) |
            Q(person__last_name__icontains=search) |
            Q(event__title__icontains=search)
        )
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if start_date:
        bookings = bookings.filter(event__starts_at__date__gte=start_date)
    if end_date:
        bookings = bookings.filter(event__starts_at__date__lte=end_date)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=reservas.csv'
        writer = csv.writer(response)
        writer.writerow(['Evento', 'Data', 'Hora', 'Cliente', 'Estado', 'Criada em'])
        for booking in bookings.iterator():
            writer.writerow([
                booking.event.title,
                booking.event.starts_at.strftime('%Y-%m-%d'),
                booking.event.starts_at.strftime('%H:%M'),
                booking.person.full_name,
                booking.status,
                booking.created_at.strftime('%Y-%m-%d %H:%M'),
            ])
        return response

    paginator = Paginator(bookings, 20)
    page_number = request.GET.get('page')
    bookings = paginator.get_page(page_number)

    return render(request, 'core/booking_list.html', {
        'bookings': bookings,
        'search': search,
        'status_filter': status_filter,
        'start_date': start_date_raw,
        'end_date': end_date_raw,
        'status_choices': Booking.Status.choices,
    })


@role_required(["admin", "staff"])
def booking_add(request):
    """Adicionar nova reserva."""
    org = request.organization

    if request.method == 'POST':
        form = BookingForm(request.POST, organization=org)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.organization = org
            booking.save()
            messages.success(request, 'Reserva criada com sucesso!')
            return redirect('core:booking_list')
    else:
        form = BookingForm(organization=org)

    return render(request, 'core/booking_form.html', {'form': form, 'title': 'Nova Reserva'})


@role_required(["admin", "staff"])
def organization_settings(request):
    """
    Painel Central de Parametrização do Protocolo ACR & Proform SC.
    Permite editar dados institucionais, seguradora, mediador, projeto/candidatura IPDJ,
    direção técnica, espaços/instalações e regras de transferência financeira.
    """
    org = request.organization
    protocol_config = org.get_protocol_config()

    if request.method == 'POST':
        form = ProtocolConfigurationForm(request.POST, instance=protocol_config, organization=org)
        # Atualizar também campos da organização se presentes
        gym_fee = request.POST.get('gym_monthly_fee')
        wellness_fee = request.POST.get('wellness_monthly_fee')
        if gym_fee is not None:
            try:
                org.gym_monthly_fee = Decimal(str(gym_fee))
            except Exception:
                pass
        if wellness_fee is not None:
            try:
                org.wellness_monthly_fee = Decimal(str(wellness_fee))
            except Exception:
                pass
        org.save(update_fields=['gym_monthly_fee', 'wellness_monthly_fee'])

        if form.is_valid():
            form.save()
            messages.success(request, 'Parametrização do Protocolo e Seguros atualizada com sucesso!')
            return redirect('core:settings')
        else:
            messages.error(request, 'Existem erros no formulário de parametrização. Por favor verifique os campos.')
    else:
        form = ProtocolConfigurationForm(instance=protocol_config, organization=org)

    resources = Resource.objects.filter(organization=org).order_by('name')
    instructors = Instructor.objects.filter(organization=org).order_by('first_name')

    context = {
        'organization': org,
        'protocol_config': protocol_config,
        'form': form,
        'resources': resources,
        'instructors': instructors,
        'title': 'Parametrização Geral do Protocolo e Entidades',
    }
    return render(request, 'core/settings.html', context)


@role_required(["admin", "staff"])
def schedule_view(request):
    """Vista do horário/agenda."""
    org = request.organization

    # Data selecionada
    selected_date = request.GET.get('date')
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    # Eventos do dia
    events = Event.objects.filter(
        organization=org,
        starts_at__date=selected_date
    ).select_related('resource', 'modality', 'instructor').order_by('starts_at')

    return render(request, 'core/schedule.html', {
        'events': events,
        'selected_date': selected_date
    })


# ==========================================
# MÓDULO DE CAIXA E BALCÃO DE PAGAMENTOS
# ==========================================

@role_required(["admin", "staff"])
def cashier_dashboard(request):
    """Balcão de caixa: resumo diário, cobranças e histórico recente."""
    org = request.organization
    today = timezone.now().date()

    # Métricas do dia de hoje
    today_payments = Payment.objects.filter(
        organization=org,
        paid_date=today,
        status=Payment.Status.COMPLETED
    )
    total_today = today_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    cash_today = today_payments.filter(method=Payment.Method.CASH).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    mbway_today = today_payments.filter(method=Payment.Method.MBWAY).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    card_today = today_payments.filter(method__in=[Payment.Method.CARD, Payment.Method.TRANSFER]).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Filtros e pesquisa
    search = request.GET.get('search', '').strip()
    method_filter = request.GET.get('method', '').strip()
    date_filter = request.GET.get('date', '').strip()

    payments_qs = Payment.objects.filter(organization=org).select_related('person').order_by('-paid_date', '-created_at')

    if search:
        payments_qs = payments_qs.filter(
            Q(person__first_name__icontains=search) |
            Q(person__last_name__icontains=search) |
            Q(person__nif__icontains=search) |
            Q(description__icontains=search)
        )
    if method_filter:
        payments_qs = payments_qs.filter(method=method_filter)
    if date_filter:
        try:
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            payments_qs = payments_qs.filter(paid_date=d)
        except ValueError:
            pass

    paginator = Paginator(payments_qs, 20)
    page_number = request.GET.get('page')
    payments_page = paginator.get_page(page_number)

    # Clientes ativos para atalho de pesquisa rápida
    active_clients = Person.objects.filter(organization=org, status='active').order_by('first_name', 'last_name')[:15]

    context = {
        'total_today': total_today,
        'cash_today': cash_today,
        'mbway_today': mbway_today,
        'card_today': card_today,
        'count_today': today_payments.count(),
        'payments': payments_page,
        'search': search,
        'method_filter': method_filter,
        'date_filter': date_filter,
        'method_choices': Payment.Method.choices,
        'active_clients': active_clients,
        'today': today,
    }
    return render(request, 'core/cashier.html', context)


@role_required(["admin", "staff"])
def payment_create(request):
    """Registo de novo pagamento no balcão de caixa."""
    org = request.organization
    initial_data = {}
    client_id = request.GET.get('client_id')
    selected_client = None

    if client_id and client_id.isdigit():
        selected_client = Person.objects.filter(organization=org, pk=int(client_id)).first()
        if selected_client:
            initial_data['person'] = selected_client
            active_sub = selected_client.active_subscription
            if active_sub:
                initial_data['payment_plan'] = active_sub.payment_plan
                initial_data['amount'] = active_sub.payment_plan.price
                initial_data['description'] = f"Mensalidade - {active_sub.payment_plan.name}"

    if request.method == 'POST':
        form = PaymentRegistrationForm(request.POST, organization=org)
        if form.is_valid():
            person = form.cleaned_data['person']
            payment_plan = form.cleaned_data['payment_plan']
            amount = form.cleaned_data['amount']
            method = form.cleaned_data['method']
            paid_date = form.cleaned_data['paid_date']
            description = form.cleaned_data['description'] or (f"Pagamento - {payment_plan.name}" if payment_plan else "Pagamento Avulso")
            notes = form.cleaned_data['notes']
            auto_activate = form.cleaned_data['auto_activate']

            payment = Payment.objects.create(
                organization=org,
                person=person,
                amount=amount,
                method=method,
                status=Payment.Status.COMPLETED,
                paid_date=paid_date,
                description=description,
                notes=notes
            )

            # Atualizar subscrição e créditos automaticamente
            if payment_plan and auto_activate:
                existing_sub = person.subscriptions.filter(payment_plan=payment_plan, status=ClientSubscription.Status.ACTIVE).first()

                if payment_plan.plan_type == PaymentPlan.PlanType.CREDITS:
                    credits_to_add = payment_plan.credits_included
                    expire_date = paid_date + timedelta(days=payment_plan.credits_validity_days)

                    if existing_sub:
                        credits_before = existing_sub.remaining_credits
                        existing_sub.remaining_credits += credits_to_add
                        existing_sub.credits_expire_date = expire_date
                        existing_sub.is_paid = True
                        existing_sub.payment_date = paid_date
                        existing_sub.save()
                        sub_for_history = existing_sub
                        credits_after = existing_sub.remaining_credits
                    else:
                        credits_before = 0
                        new_sub = ClientSubscription.objects.create(
                            organization=org,
                            person=person,
                            payment_plan=payment_plan,
                            status=ClientSubscription.Status.ACTIVE,
                            start_date=paid_date,
                            end_date=expire_date,
                            remaining_credits=credits_to_add,
                            credits_expire_date=expire_date,
                            is_paid=True,
                            payment_date=paid_date,
                            notes=f"Criada no pagamento #{payment.pk}"
                        )
                        sub_for_history = new_sub
                        credits_after = credits_to_add

                    CreditHistory.objects.create(
                        organization=org,
                        person=person,
                        subscription=sub_for_history,
                        action=CreditHistory.Action.PURCHASE,
                        credits_amount=credits_to_add,
                        credits_before=credits_before,
                        credits_after=credits_after,
                        description=f"Compra pack {credits_to_add} créditos (Pagamento #{payment.pk})"
                    )

                elif payment_plan.plan_type == PaymentPlan.PlanType.MONTHLY:
                    end_date = paid_date + timedelta(days=30 * payment_plan.duration_months)
                    if existing_sub:
                        existing_sub.start_date = paid_date
                        existing_sub.end_date = end_date
                        existing_sub.is_paid = True
                        existing_sub.payment_date = paid_date
                        existing_sub.save()
                    else:
                        ClientSubscription.objects.create(
                            organization=org,
                            person=person,
                            payment_plan=payment_plan,
                            status=ClientSubscription.Status.ACTIVE,
                            start_date=paid_date,
                            end_date=end_date,
                            is_paid=True,
                            payment_date=paid_date,
                            notes=f"Criada no pagamento #{payment.pk}"
                        )

            messages.success(request, f"Pagamento de €{payment.amount:.2f} ({payment.get_method_display()}) registado com sucesso para {person.full_name}!")
            return redirect('core:payment_receipt', payment_id=payment.pk)
    else:
        form = PaymentRegistrationForm(initial=initial_data, organization=org)

    context = {
        'form': form,
        'selected_client': selected_client,
        'title': 'Registar Pagamento no Caixa'
    }
    return render(request, 'core/payment_form.html', context)


@role_required(["admin", "staff"])
def client_pay(request, client_id):
    """Atalho para pagar diretamente na ficha de um cliente."""
    return redirect(f"{reverse('core:payment_add')}?client_id={client_id}")


@role_required(["admin", "staff"])
def payment_receipt(request, payment_id):
    """Comprovativo / Recibo de pagamento pronto para impressão ou consulta."""
    org = request.organization
    payment = get_object_or_404(Payment, pk=payment_id, organization=org)

    context = {
        'payment': payment,
        'client': payment.person,
        'organization': org,
        'today': timezone.now().date(),
    }
    return render(request, 'core/payment_receipt.html', context)


@role_required(["admin", "staff"])
def client_subscribe(request, client_id):
    """Associar um plano de mensalidade ou créditos diretamente ao atleta."""
    org = request.organization
    client = get_object_or_404(Person, pk=client_id, organization=org)

    if request.method == 'POST':
        form = ClientSubscriptionForm(request.POST, organization=org)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.organization = org
            sub.person = client
            if sub.payment_plan.plan_type == PaymentPlan.PlanType.CREDITS:
                sub.remaining_credits = sub.payment_plan.credits_included
                if not sub.end_date:
                    sub.end_date = sub.start_date + timedelta(days=sub.payment_plan.credits_validity_days)
                sub.credits_expire_date = sub.end_date
            elif sub.payment_plan.plan_type == PaymentPlan.PlanType.MONTHLY:
                if not sub.end_date:
                    sub.end_date = sub.start_date + timedelta(days=30 * sub.payment_plan.duration_months)
            sub.save()
            messages.success(request, f"Plano {sub.payment_plan.name} atribuído a {client.full_name} com sucesso!")
            return redirect('core:client_detail', pk=client.pk)
    else:
        form = ClientSubscriptionForm(organization=org)

    context = {
        'form': form,
        'client': client,
        'title': f"Subscrever Plano - {client.full_name}"
    }
    return render(request, 'core/subscription_form.html', context)


@role_required(["admin", "staff"])
def client_resend_welcome(request, client_id):
    """Reenviar e-mail de boas-vindas e apólice de seguro."""
    org = request.organization
    client = get_object_or_404(Person, pk=client_id, organization=org)
    if not client.email:
        messages.error(request, "Este atleta não possui endereço de e-mail registado.")
        return redirect('core:client_detail', pk=client.pk)

    sent = send_athlete_welcome_email(client, request)
    if sent:
        messages.success(request, f"E-mail de boas-vindas e apólice reenviado com sucesso para {client.email}!")
    else:
        messages.warning(request, f"Não foi possível enviar o e-mail para {client.email}. Consulte o histórico de notificações.")
    return redirect('core:client_detail', pk=client.pk)


@role_required(["admin", "staff"])
def google_drive_sync_view(request):
    """Painel de sincronização da lista de praticantes com o Google Drive da ACR."""
    org = request.organization
    total_athletes = Person.objects.filter(organization=org).count()
    logs = GoogleDriveSyncLog.objects.filter(organization=org).order_by('-created_at')[:20]
    last_log = logs.first()

    context = {
        'total_athletes': total_athletes,
        'logs': logs,
        'last_log': last_log,
        'title': 'Sincronização Google Drive da ACR'
    }
    return render(request, 'core/google_drive_sync.html', context)


@role_required(["admin", "staff"])
@require_http_methods(["POST"])
def google_drive_trigger_sync(request):
    """Dispara a sincronização imediata dos praticantes para a Google Drive."""
    org = request.organization
    from .services.google_drive import sync_athletes_to_google_drive
    result = sync_athletes_to_google_drive(org)
    if result.get('success'):
        messages.success(request, result.get('message', 'Sincronização concluída com sucesso!'))
    else:
        messages.error(request, "Ocorreu um erro ao sincronizar com a Google Drive.")
    return redirect('core:google_drive_sync')


@role_required(["admin", "staff"])
def export_athletes_sheet(request):
    """Exportar lista de atletas consolidada em Excel (.xlsx) ou CSV."""
    org = request.organization
    file_format = request.GET.get('format', 'xlsx').lower()
    timestamp_str = timezone.now().strftime('%Y%m%d_%H%M')

    if file_format == 'csv':
        from .services.google_drive import generate_athletes_csv
        csv_data = generate_athletes_csv(org)
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="Atletas_ACR_Proform_{timestamp_str}.csv"'
        return response
    else:
        from .services.google_drive import generate_athletes_excel
        excel_data = generate_athletes_excel(org)
        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="Atletas_ACR_Proform_{timestamp_str}.xlsx"'
        return response


@role_required(["admin", "staff", "instructor"])
def event_checkin(request, event_id):
    """Interface de lista de chamada e check-in no tapete para instrutores e receção."""
    org = request.organization
    event = get_object_or_404(
        Event.objects.select_related('modality', 'resource', 'instructor'),
        pk=event_id,
        organization=org
    )
    bookings = event.bookings.select_related('person').order_by('person__first_name', 'person__last_name')
    checked_in_count = bookings.filter(status=Booking.Status.CHECKED_IN).count()

    # Contar atletas com seguro vencido ou em falta presentes na lista da aula
    expired_insurance_count = sum(
        1 for b in bookings if not b.person.insurance_status.get('is_valid', False)
    )

    # Lista de atletas disponíveis para adicionar rapidamente (que ainda não têm reserva nesta aula)
    existing_person_ids = bookings.values_list('person_id', flat=True)
    available_athletes = Person.objects.filter(
        organization=org, status='active'
    ).exclude(id__in=existing_person_ids).order_by('first_name', 'last_name')

    context = {
        'event': event,
        'bookings': bookings,
        'checked_in_count': checked_in_count,
        'expired_insurance_count': expired_insurance_count,
        'available_athletes': available_athletes,
        'title': f"Check-in no Tapete: {event.title}"
    }
    return render(request, 'core/mat_checkin.html', context)


@role_required(["admin", "staff", "instructor"])
@require_http_methods(["POST"])
def booking_toggle_checkin(request, booking_id):
    """Alternar o estado da presença na aula (checked_in, no_show, confirmed)."""
    org = request.organization
    booking = get_object_or_404(Booking.objects.select_related('person', 'event'), pk=booking_id, organization=org)
    new_status = request.POST.get('status')

    if new_status in [Booking.Status.CHECKED_IN, Booking.Status.NO_SHOW, Booking.Status.CONFIRMED]:
        booking.status = new_status
        booking.save(update_fields=['status'])
        status_label = "Presente" if new_status == Booking.Status.CHECKED_IN else ("Falta" if new_status == Booking.Status.NO_SHOW else "Pendente")
        messages.success(request, f"{booking.person.full_name}: marcado como '{status_label}' no tapete.")
    else:
        messages.error(request, "Estado de presença inválido.")

    return redirect('core:event_checkin', event_id=booking.event.pk)


@role_required(["admin", "staff", "instructor"])
@require_http_methods(["POST"])
def event_quick_add_attendance(request, event_id):
    """Adicionar atleta que apareceu no treino sem reserva prévia, consumindo crédito ou validando plano."""
    org = request.organization
    event = get_object_or_404(Event, pk=event_id, organization=org)
    person_id = request.POST.get('person_id')

    if not person_id:
        messages.error(request, "Selecione um praticante para adicionar à aula.")
        return redirect('core:event_checkin', event_id=event.pk)

    try:
        person_id = int(person_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'ID inválido'}, status=400)

    person = get_object_or_404(Person, pk=person_id, organization=org)

    # Verificar se já tem reserva
    existing_booking = Booking.objects.filter(event=event, person=person).first()
    if existing_booking:
        existing_booking.status = Booking.Status.CHECKED_IN
        existing_booking.save(update_fields=['status'])
        messages.info(request, f"{person.full_name} já estava inscrito e foi marcado como Presente.")
        return redirect('core:event_checkin', event_id=event.pk)

    # Verificar subscrição ativa
    active_sub = person.active_subscription
    subscription_used = None
    note = ""

    if active_sub:
        if active_sub.payment_plan.plan_type == PaymentPlan.PlanType.CREDITS:
            if active_sub.has_credits():
                credits_before = active_sub.remaining_credits
                active_sub.use_credit()
                subscription_used = active_sub
                credits_after = active_sub.remaining_credits
                CreditHistory.objects.create(
                    organization=org,
                    person=person,
                    subscription=active_sub,
                    action=CreditHistory.Action.USE,
                    credits_amount=-1,
                    credits_before=credits_before,
                    credits_after=credits_after,
                    description=f"Presença na aula {event.title} ({event.starts_at:%d/%m/%Y %H:%M})"
                )
                note = f"1 crédito debitado ({credits_after} restantes)."
            else:
                note = "Saldo de créditos esgotado - cobrar aula no Caixa!"
        else:
            subscription_used = active_sub
            note = "Mensalidade ativa confirmada."
    else:
        note = "Sem plano ativo - pagamento pendente de registo no Caixa!"

    # Criar booking com status checked_in
    booking = Booking.objects.create(
        organization=org,
        event=event,
        person=person,
        status=Booking.Status.CHECKED_IN,
        subscription_used=subscription_used,
        is_paid=bool(subscription_used)
    )

    messages.success(request, f"Atleta {person.full_name} entrou no tapete! {note}")
    return redirect('core:event_checkin', event_id=event.pk)


# ==============================================================================
# JANELA 4: SUPERVISÃO FINANCEIRA ACR E DIVISÃO TRIPARTIDA DO PROTOCOLO
# ==============================================================================

@protocol_access_required(require_approval_power=False)
def protocol_supervision_dashboard(request):
    """
    Portal de Supervisão Financeira da ACR e do Protocolo ACR & Proform SC.
    Apresenta a divisão tripartida da receita, comissões de instrutores e histórico de fechos de contas.
    """
    org = request.organization
    today = timezone.now().date()

    # Período selecionado (por defeito o mês corrente)
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today.replace(day=1)
    else:
        start_date = today.replace(day=1)

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
    else:
        end_date = today

    # Calcular a divisão tripartida
    split_data = calculate_period_protocol_split(org, start_date, end_date)

    # Fechos oficiais já registados
    settlements = ProtocolPeriodSettlement.objects.filter(
        organization=org
    ).order_by('-period_end', '-created_at')[:25]

    # Comissões de instrutores do período com registo individual
    commissions = InstructorCommission.objects.filter(
        organization=org,
        event__starts_at__date__gte=start_date,
        event__starts_at__date__lte=end_date
    ).select_related('instructor', 'event', 'event__modality').order_by('-event__starts_at')

    context = {
        'organization': org,
        'start_date': start_date,
        'end_date': end_date,
        'split_data': split_data,
        'settlements': settlements,
        'commissions': commissions,
        'today': today,
    }
    return render(request, 'core/protocol_supervision.html', context)


@protocol_access_required(require_approval_power=False)
@require_http_methods(["POST"])
def protocol_settlement_create(request):
    """
    Gera ou atualiza um fecho de contas oficial do protocolo com base no período filtrado.
    """
    org = request.organization
    start_date_str = request.POST.get('start_date')
    end_date_str = request.POST.get('end_date')
    notes = request.POST.get('notes', '').strip()

    if not start_date_str or not end_date_str:
        messages.error(request, "Indique as datas de início e fim para emitir o fecho de contas.")
        return redirect('core:protocol_supervision')

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Formato de data inválido.")
        return redirect('core:protocol_supervision')

    if start_date > end_date:
        messages.error(request, "A data inicial não pode ser posterior à data final.")
        return redirect('core:protocol_supervision')

    settlement = create_or_update_period_settlement(org, start_date, end_date, notes=notes)
    messages.success(
        request,
        f"Fecho de Contas ({start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}) gerado com sucesso!"
    )
    return redirect('core:protocol_settlement_detail', settlement_id=settlement.pk)


@protocol_access_required(require_approval_power=False)
def protocol_settlement_detail(request, settlement_id):
    """
    Exibe a declaração detalhada de fecho de contas do protocolo, com layout oficial pronto para impressão.
    """
    org = request.organization
    settlement = get_object_or_404(ProtocolPeriodSettlement, pk=settlement_id, organization=org)

    # Obter os dados discriminados desse período
    split_data = calculate_period_protocol_split(org, settlement.period_start, settlement.period_end)

    context = {
        'organization': org,
        'settlement': settlement,
        'split_data': split_data,
        'today': timezone.now().date(),
    }
    return render(request, 'core/protocol_settlement_detail.html', context)


@protocol_access_required(require_approval_power=True)
@require_http_methods(["POST"])
def protocol_settlement_toggle_status(request, settlement_id):
    """
    Atualiza o estado de um fecho de contas (Rascunho -> Aprovado -> Liquidado).
    """
    org = request.organization
    settlement = get_object_or_404(ProtocolPeriodSettlement, pk=settlement_id, organization=org)

    new_status = request.POST.get('status')
    if new_status in [s.value for s in ProtocolPeriodSettlement.Status]:
        settlement.status = new_status
    else:
        # Progressão automática por defeito
        if settlement.status == ProtocolPeriodSettlement.Status.DRAFT:
            settlement.status = ProtocolPeriodSettlement.Status.APPROVED
        elif settlement.status == ProtocolPeriodSettlement.Status.APPROVED:
            settlement.status = ProtocolPeriodSettlement.Status.SETTLED
        elif settlement.status == ProtocolPeriodSettlement.Status.SETTLED:
            settlement.status = ProtocolPeriodSettlement.Status.DRAFT

    if settlement.status == ProtocolPeriodSettlement.Status.SETTLED:
        settlement.settled_at = timezone.now()
    else:
        settlement.settled_at = None

    settlement.save()
    messages.success(request, f"Estado do fecho atualizado para '{settlement.get_status_display()}'.")
    return redirect('core:protocol_settlement_detail', settlement_id=settlement.pk)


@role_required(["admin", "staff"])
@require_http_methods(["POST"])
def instructor_commission_toggle_paid(request, commission_id):
    """
    Alterna o estado de pagamento de uma comissão individual de instrutor.
    """
    org = request.organization
    commission = get_object_or_404(InstructorCommission, pk=commission_id, organization=org)

    commission.is_paid = not commission.is_paid
    if commission.is_paid:
        commission.payment_date = timezone.now().date()
    else:
        commission.payment_date = None
    commission.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_paid': commission.is_paid,
            'payment_date': commission.payment_date.strftime('%d/%m/%Y') if commission.payment_date else None,
            'message': f"Comissão de {commission.instructor.full_name} marcada como {'Paga' if commission.is_paid else 'Pendente'}."
        })

    messages.success(
        request,
        f"Comissão de {commission.instructor.full_name} marcada como {'Paga' if commission.is_paid else 'Pendente'}."
    )
    return redirect(request.META.get('HTTP_REFERER', 'core:protocol_supervision'))


# ==============================================================================
# GESTÃO DA ASSOCIAÇÃO ACR, QUIOSQUE DE TAPETE & CARTÃO DIGITAL
# ==============================================================================

@role_required(["admin", "staff"])
def member_card_view(request, pk):
    """Exibe o Cartão Digital oficial de Sócio e Praticante da ACR."""
    org = request.organization
    person = get_object_or_404(Person, pk=pk, organization=org)
    card_data = get_membership_card_data(person)
    return render(request, "core/membership_card.html", card_data)


@role_required(["admin", "staff", "instructor", "proform_director"])
@require_http_methods(["POST"])
def athlete_graduation_add(request, pk):
    """Regista um novo exame/graduação de cinto para o atleta."""
    if not (request.user.is_superuser or getattr(request, 'can_manage_sports', False)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Apenas a direção técnica ou treinadores credenciados podem registar graduações.")
    org = request.organization
    person = get_object_or_404(Person, pk=pk, organization=org)

    modality_id = request.POST.get("modality")
    rank_name = request.POST.get("rank_name", "").strip()
    rank_order = request.POST.get("rank_order", "1").strip()
    awarded_date_str = request.POST.get("awarded_date", "").strip()
    examiner_id = request.POST.get("examiner")
    examiner_name = request.POST.get("examiner_name", "").strip()
    certificate_number = request.POST.get("certificate_number", "").strip()
    classes_attended_count = request.POST.get("classes_attended_count", "").strip()
    notes = request.POST.get("notes", "").strip()

    if not rank_name or not modality_id:
        messages.error(request, "Modalidade e nome da graduação/cinto são obrigatórios.")
        return redirect("core:client_detail", pk=person.pk)

    try:
        modality_id = int(modality_id)
    except (ValueError, TypeError):
        messages.error(request, "Modalidade inválida.")
        return redirect("core:client_detail", pk=person.pk)

    modality = get_object_or_404(Modality, pk=modality_id, organization=org)

    examiner = None
    if examiner_id:
        examiner = Instructor.objects.filter(pk=examiner_id, organization=org).first()
        if examiner and not examiner_name:
            examiner_name = examiner.full_name

    awarded_date = parse_date(awarded_date_str) if awarded_date_str else timezone.now().date()

    try:
        rank_order_int = int(rank_order)
    except ValueError:
        rank_order_int = 1

    # Contabilização automática de presenças nos treinos no tapete se não for preenchido
    if classes_attended_count and classes_attended_count.isdigit():
        attended_count = int(classes_attended_count)
    else:
        attended_count = Booking.objects.filter(
            organization=org,
            person=person,
            event__modality=modality,
            status=Booking.Status.CHECKED_IN
        ).count()

    graduation = AthleteGraduation.objects.create(
        organization=org,
        person=person,
        modality=modality,
        rank_name=rank_name,
        rank_order=rank_order_int,
        awarded_date=awarded_date,
        examiner=examiner,
        examiner_name=examiner_name,
        certificate_number=certificate_number,
        classes_attended_count=attended_count,
        notes=notes,
    )

    messages.success(request, f"Graduação '{rank_name}' em {modality.name} atribuída a {person.full_name} com sucesso ({attended_count} treinos contabilizados).")
    return redirect("core:client_detail", pk=person.pk)


@role_required(["admin", "staff"])
def kiosk_view(request):
    """Interface Quiosque em ecrã inteiro para tablet na entrada do pavilhão/tapete."""
    org = request.organization
    active_event = get_active_event_for_facility(org)

    # Próximas aulas de hoje
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    todays_events = Event.objects.filter(
        organization=org,
        starts_at__gte=timezone.now() - timedelta(hours=1),
        starts_at__lte=today_end
    ).select_related('resource', 'modality', 'instructor').order_by('starts_at')[:8]

    context = {
        "organization": org,
        "active_event": active_event,
        "todays_events": todays_events,
        "protocol_config": org.get_protocol_config(),
    }
    return render(request, "core/kiosk.html", context)


@role_required(["admin", "staff"])
@require_http_methods(["POST"])
def kiosk_checkin_api(request):
    """Endpoint de validação e check-in imediato para o Quiosque do Pavilhão."""
    import json
    org = request.organization

    identifier = ""
    event_id = None

    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body.decode("utf-8"))
            identifier = payload.get("identifier", "").strip()
            event_id = payload.get("event_id")
        except Exception:
            return JsonResponse({"success": False, "status": "red", "message": "JSON inválido."}, status=400)
    else:
        identifier = request.POST.get("identifier", "").strip()
        event_id = request.POST.get("event_id")

    if not identifier:
        return JsonResponse({
            "success": False,
            "status": "red",
            "title": "Código Ausente",
            "message": "Por favor aproxime o QR Code ou digite o Número de Sócio / NIF."
        })

    try:
        specific_event_id = int(event_id) if event_id else None
    except (ValueError, TypeError):
        specific_event_id = None

    result = process_kiosk_checkin(org, identifier, specific_event_id=specific_event_id)
    return JsonResponse(result)


@acr_required(require_direction=True)
def association_governance_view(request):
    """Painel institucional da Associação ACR: Órgãos Sociais, Mandatos e Caderno de Sócios."""
    org = request.organization
    bodies = GoverningBody.objects.filter(organization=org).prefetch_related('members__person')

    # Estatísticas de Sócios da ACR
    total_members = Person.objects.filter(organization=org, member_category=Person.MemberCategory.SOCIO).count()
    fees_up_to_date = Person.objects.filter(
        organization=org,
        member_category=Person.MemberCategory.SOCIO,
        membership_fee_status=Person.MembershipFeeStatus.UP_TO_DATE
    ).count()
    fees_overdue = Person.objects.filter(
        organization=org,
        member_category=Person.MemberCategory.SOCIO,
        membership_fee_status=Person.MembershipFeeStatus.OVERDUE
    ).count()
    fees_exempt = Person.objects.filter(
        organization=org,
        member_category=Person.MemberCategory.SOCIO,
        membership_fee_status=Person.MembershipFeeStatus.EXEMPT
    ).count()

    active_bodies = bodies.filter(is_active=True)
    board = active_bodies.filter(body_type=GoverningBody.BodyType.BOARD).first()
    general_assembly = active_bodies.filter(body_type=GoverningBody.BodyType.GENERAL_ASSEMBLY).first()
    fiscal_council = active_bodies.filter(body_type=GoverningBody.BodyType.FISCAL_COUNCIL).first()

    context = {
        "organization": org,
        "bodies": bodies,
        "active_bodies": active_bodies,
        "board": board,
        "general_assembly": general_assembly,
        "fiscal_council": fiscal_council,
        "total_members": total_members,
        "fees_up_to_date": fees_up_to_date,
        "fees_overdue": fees_overdue,
        "fees_exempt": fees_exempt,
        "protocol_config": org.get_protocol_config(),
    }
    return render(request, "core/association_governance.html", context)



