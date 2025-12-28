from django.shortcuts import render, get_object_or_404, redirect
from .auth_views import role_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Person, Instructor, Modality, Event, Resource, Payment, Booking
from .forms import PersonForm, InstructorForm, ModalityForm, EventForm, BookingForm, ResourceForm


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
    clients = Person.objects.filter(organization=org)

    # Filtros
    search = request.GET.get('search')
    status_filter = request.GET.get('status')

    if search:
        clients = clients.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    if status_filter:
        clients = clients.filter(status=status_filter)

    # Paginação
    paginator = Paginator(clients, 20)
    page_number = request.GET.get('page')
    clients = paginator.get_page(page_number)

    context = {
        'clients': clients,
        'search': search,
        'status_filter': status_filter,
        'status_choices': Person.Status.choices,
    }
    return render(request, 'core/client_list.html', context)


@role_required(["admin", "staff"])
def client_detail(request, pk):
    """Detalhes de um cliente específico."""
    client = get_object_or_404(Person, pk=pk, organization=request.organization)
    recent_bookings = client.bookings.order_by('-created_at')[:5]
    recent_payments = client.payments.order_by('-created_at')[:5]

    context = {
        'client': client,
        'recent_bookings': recent_bookings,
        'recent_payments': recent_payments,
    }
    return render(request, 'core/client_detail.html', context)


@role_required(["admin", "staff"])
def client_create(request):
    """Criar novo cliente."""
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, organization=request.organization)
        if form.is_valid():
            client = form.save(commit=False)
            client.organization = request.organization
            client.save()
            messages.success(request, f'Cliente {client.full_name} criado com sucesso!')
            return redirect('client_detail', pk=client.pk)
    else:
        form = PersonForm(organization=request.organization)

    return render(request, 'core/client_form.html', {'form': form, 'title': 'Novo Cliente'})


@role_required(["admin", "staff"])
def client_edit(request, pk):
    """Editar cliente existente."""
    client = get_object_or_404(Person, pk=pk, organization=request.organization)

    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, instance=client, organization=request.organization)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cliente {client.full_name} atualizado com sucesso!')
            return redirect('client_detail', pk=client.pk)
    else:
        form = PersonForm(instance=client, organization=request.organization)

    return render(request, 'core/client_form.html', {
        'form': form,
        'client': client,
        'title': 'Editar Cliente'
    })


@role_required(["admin", "staff"])
def client_add(request):
    """Adicionar novo cliente."""
    org = request.organization

    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, organization=org)
        if form.is_valid():
            client = form.save(commit=False)
            client.organization = org
            client.save()
            messages.success(request, f'Cliente {client.full_name} criado com sucesso!')
            return redirect('core:client_detail', pk=client.pk)
    else:
        form = PersonForm(organization=org)

    return render(request, 'core/client_form.html', {
        'form': form,
        'title': 'Adicionar Cliente',
        'action': 'add'
    })


# INSTRUTORES VIEWS
@role_required(["admin", "staff"])
def instructor_list(request):
    """Listagem de instrutores."""
    org = request.organization
    instructors = Instructor.objects.filter(organization=org)

    search = request.GET.get('search')
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
            return redirect('instructor_detail', pk=instructor.pk)
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
    modalities = Modality.objects.filter(organization=org)

    context = {'modalities': modalities}
    return render(request, 'core/modality_list.html', context)


@role_required(["admin", "staff"])
def modality_create(request):
    """Criar nova modalidade."""
    if request.method == 'POST':
        form = ModalityForm(request.POST)
        if form.is_valid():
            modality = form.save(commit=False)
            modality.organization = request.organization
            modality.save()
            messages.success(request, f'Modalidade {modality.name} criada com sucesso!')
            return redirect('modality_list')
    else:
        form = ModalityForm()

    return render(request, 'core/modality_form.html', {'form': form, 'title': 'Nova Modalidade'})


@role_required(["admin", "staff"])
def modality_edit(request, pk):
    """Editar modalidade existente."""
    modality = get_object_or_404(Modality, pk=pk, organization=request.organization)

    if request.method == 'POST':
        form = ModalityForm(request.POST, instance=modality)
        if form.is_valid():
            form.save()
            messages.success(request, f'Modalidade {modality.name} atualizada com sucesso!')
            return redirect('modality_list')
    else:
        form = ModalityForm(instance=modality)

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
        form = ModalityForm(request.POST)
        if form.is_valid():
            modality = form.save(commit=False)
            modality.organization = org
            modality.save()
            messages.success(request, f'Modalidade {modality.name} criada com sucesso!')
            return redirect('core:modality_list')
    else:
        form = ModalityForm()

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
        form = ResourceForm(request.POST)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.organization = org
            resource.save()
            messages.success(request, f'Espaço "{resource.name}" criado com sucesso!')
            return redirect('core:resource_list')
    else:
        form = ResourceForm()

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
        form = ResourceForm(request.POST, instance=resource)
        if form.is_valid():
            form.save()
            messages.success(request, f'Espaço "{resource.name}" atualizado com sucesso!')
            return redirect('core:resource_list')
    else:
        form = ResourceForm(instance=resource)

    return render(request, 'core/resource_form.html', {
        'form': form,
        'resource': resource,
        'title': 'Editar Espaço',
        'action': 'edit'
    })


# GANTT E EVENTOS
@role_required(["admin", "staff"])
def gantt_system(request):
    """Vista do Sistema Gantt completo para gestão de espaços."""
    org = request.organization

    # Carregar dados necessários para o Sistema Gantt
    resources = Resource.objects.filter(organization=org).order_by('name')
    instructors = Instructor.objects.filter(organization=org, is_active=True).order_by('first_name', 'last_name')
    modalities = Modality.objects.filter(organization=org, is_active=True).order_by('entity_type', 'name')

    # Estatísticas rápidas para o dashboard do Gantt
    today = timezone.now().date()
    today_events = Event.objects.filter(
        organization=org,
        starts_at__date=today
    ).count()

    context = {
        'resources': resources,
        'instructors': instructors,
        'modalities': modalities,
        'today_events': today_events,
        'page_title': 'Sistema Gantt - Gestão de Espaços',
    }

    return render(request, 'core/gantt_system.html', context)


@role_required(["admin", "staff"])
def gantt_view(request):
    """Manter compatibilidade com URL antiga, redirecionar para o novo Sistema Gantt."""
    return redirect('gantt_system')


@role_required(["admin", "staff"])
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
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organization = request.organization
            event.save()
            messages.success(request, f'Aula {event.title} criada com sucesso!')
            return redirect('gantt_view')
    else:
        form = EventForm()
        # Filtrar recursos da organização
        form.fields['resource'].queryset = Resource.objects.filter(organization=request.organization)

    return render(request, 'core/event_form.html', {'form': form, 'title': 'Nova Aula'})


@role_required(["admin", "staff"])
def event_list(request):
    """Listagem de eventos/aulas."""
    org = request.organization

    # Base queryset
    events_qs = Event.objects.filter(organization=org).select_related('resource', 'modality', 'instructor').order_by('-starts_at')

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

    # Paginação
    paginator = Paginator(events_qs, 20)
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)

    # Enriquecer eventos com classes de ocupação para o template
    for ev in events:
        try:
            booked = (
                ev.bookings_count
                if hasattr(ev, 'bookings_count')
                else ev.bookings.exclude(status=Booking.Status.CANCELLED).count()
            )
        except Exception:
            booked = ev.bookings.count()
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
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f'Aula {event.title} atualizada com sucesso!')
            return redirect('event_list')
    else:
        form = EventForm(instance=event)
        # Filtrar recursos da organização
        form.fields['resource'].queryset = Resource.objects.filter(organization=request.organization)

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
            event.save()
            messages.success(request, f'Evento {event.title} criado com sucesso!')
            return redirect('core:schedule')
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
        event.delete()
        messages.success(request, f'Evento "{title}" eliminado com sucesso!')
        return redirect('core:schedule')

    return render(request, 'core/event_confirm_delete.html', {
        'event': event
    })


@role_required(["admin", "staff"])
def booking_list(request):
    """Listagem de reservas."""
    org = request.organization
    bookings = Booking.objects.filter(organization=org).select_related("event", "person").order_by('-created_at')

    paginator = Paginator(bookings, 20)
    page_number = request.GET.get('page')
    bookings = paginator.get_page(page_number)

    return render(request, 'core/booking_list.html', {'bookings': bookings})


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
    """Vista para configurações da organização."""
    org = request.organization

    if request.method == 'POST':
        # Atualizar configurações básicas
        org.gym_monthly_fee = request.POST.get('gym_monthly_fee', org.gym_monthly_fee)
        org.wellness_monthly_fee = request.POST.get('wellness_monthly_fee', org.wellness_monthly_fee)
        org.save()
        messages.success(request, 'Configurações atualizadas com sucesso!')
        return redirect('core:settings')

    context = {
        'organization': org,
        'title': 'Configurações da Organização'
    }

    return render(request, 'core/settings.html', context)

# Views adicionais para compatibilidade
@role_required(["admin", "staff"])
def client_list(request):
    """Lista de clientes."""
    org = request.organization
    clients = Person.objects.filter(organization=org).order_by('first_name', 'last_name')

    # Filtros
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    entity = request.GET.get('entity', '')

    if search:
        clients = clients.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    if status:
        clients = clients.filter(status=status)

    if entity:
        clients = clients.filter(entity_affiliation=entity)

    paginator = Paginator(clients, 25)
    page = request.GET.get('page')
    clients = paginator.get_page(page)

    return render(request, 'core/client_list.html', {
        'clients': clients,
        'search': search,
        'status': status,
        'entity': entity
    })

@role_required(["admin", "staff"])
def instructor_list(request):
    """Lista de instrutores."""
    org = request.organization
    instructors = Instructor.objects.filter(organization=org, is_active=True).order_by('first_name', 'last_name')

    return render(request, 'core/instructor_list.html', {
        'instructors': instructors
    })

@role_required(["admin", "staff"])
def modality_list(request):
    """Lista de modalidades."""
    org = request.organization
    modalities = Modality.objects.filter(organization=org, is_active=True).order_by('entity_type', 'name')

    return render(request, 'core/modality_list.html', {
        'modalities': modalities
    })

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
