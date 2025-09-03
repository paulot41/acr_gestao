from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Person, Instructor, Modality, Event, Resource, Booking, Payment
from .forms import PersonForm, InstructorForm, ModalityForm, EventForm


@login_required
def dashboard(request):
    """Dashboard principal com estatísticas e KPIs."""
    org = request.organization

    # Estatísticas básicas
    total_clients = Person.objects.filter(organization=org, status='active').count()
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

    context = {
        'total_clients': total_clients,
        'total_instructors': total_instructors,
        'total_modalities': total_modalities,
        'upcoming_events': upcoming_events,
        'monthly_revenue': monthly_revenue,
    }
    return render(request, 'core/dashboard.html', context)


# CLIENTES VIEWS
@login_required
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


@login_required
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


@login_required
def client_create(request):
    """Criar novo cliente."""
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES)
        if form.is_valid():
            client = form.save(commit=False)
            client.organization = request.organization
            client.save()
            messages.success(request, f'Cliente {client.full_name} criado com sucesso!')
            return redirect('client_detail', pk=client.pk)
    else:
        form = PersonForm()

    return render(request, 'core/client_form.html', {'form': form, 'title': 'Novo Cliente'})


@login_required
def client_edit(request, pk):
    """Editar cliente existente."""
    client = get_object_or_404(Person, pk=pk, organization=request.organization)

    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cliente {client.full_name} atualizado com sucesso!')
            return redirect('client_detail', pk=client.pk)
    else:
        form = PersonForm(instance=client)

    return render(request, 'core/client_form.html', {
        'form': form,
        'client': client,
        'title': 'Editar Cliente'
    })


# INSTRUTORES VIEWS
@login_required
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


@login_required
def instructor_create(request):
    """Criar novo instrutor."""
    if request.method == 'POST':
        form = InstructorForm(request.POST, request.FILES)
        if form.is_valid():
            instructor = form.save(commit=False)
            instructor.organization = request.organization
            instructor.save()
            messages.success(request, f'Instrutor {instructor.full_name} criado com sucesso!')
            return redirect('instructor_list')
    else:
        form = InstructorForm()

    return render(request, 'core/instructor_form.html', {'form': form, 'title': 'Novo Instrutor'})


# MODALIDADES VIEWS
@login_required
def modality_list(request):
    """Listagem de modalidades."""
    org = request.organization
    modalities = Modality.objects.filter(organization=org)

    context = {'modalities': modalities}
    return render(request, 'core/modality_list.html', context)


@login_required
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


# GANTT E EVENTOS
@login_required
def gantt_view(request):
    """Vista Gantt para marcação de espaços."""
    org = request.organization
    resources = Resource.objects.filter(organization=org)
    instructors = Instructor.objects.filter(organization=org, is_active=True)
    modalities = Modality.objects.filter(organization=org, is_active=True)

    context = {
        'resources': resources,
        'instructors': instructors,
        'modalities': modalities,
    }
    return render(request, 'core/gantt_view.html', context)


@login_required
def events_json(request):
    """API endpoint para eventos do calendário/gantt."""
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
        events_data.append({
            'id': event.id,
            'title': event.title,
            'start': event.starts_at.isoformat(),
            'end': event.ends_at.isoformat(),
            'resourceId': event.resource.id,
            'backgroundColor': '#0d6efd',  # Por enquanto cor fixa
            'borderColor': '#0d6efd',
        })

    return JsonResponse(events_data, safe=False)


@login_required
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


@login_required
def event_list(request):
    """Listagem de eventos/aulas."""
    org = request.organization
    events = Event.objects.filter(organization=org).order_by('-starts_at')

    # Paginação
    paginator = Paginator(events, 20)
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)

    context = {'events': events}
    return render(request, 'core/event_list.html', context)
