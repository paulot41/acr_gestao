from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta
import json
from .models import Person, Membership, Product, Event, Booking, Resource, Modality, Instructor, ClassGroup
from .serializers import (
    PersonSerializer, MembershipSerializer,
    ProductSerializer, EventSerializer, BookingSerializer
)


class OrganizationMixin:
    """Filtra automaticamente por organização do utilizador."""
    def get_queryset(self):
        return super().get_queryset().filter(organization=self.request.organization)


class PersonViewSet(OrganizationMixin, viewsets.ModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [permissions.IsAuthenticated]


class EventViewSet(OrganizationMixin, viewsets.ModelViewSet):
    # Corrigir a sintaxe do Count com filter
    queryset = Event.objects.annotate(
        bookings_count=Count('bookings', filter=Q(bookings__status='confirmed'))
    )
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def book(self, request, pk=None):
        """Endpoint para fazer reserva de evento."""
        event = self.get_object()
        # Implementar lógica de booking
        return Response({'status': 'booked'})


class MembershipViewSet(OrganizationMixin, viewsets.ModelViewSet):
    queryset = Membership.objects.all()
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductViewSet(OrganizationMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]


class BookingViewSet(OrganizationMixin, viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]


# NOVOS ENDPOINTS PARA GANTT DINÂMICO

@login_required
def gantt_view(request):
    """Vista principal do Gantt dinâmico."""
    from django.shortcuts import render

    org = request.organization

    # Obter dados para o Gantt
    resources = Resource.objects.filter(organization=org, is_available=True).order_by('entity_type', 'name')
    modalities = Modality.objects.filter(organization=org, is_active=True).order_by('entity_type', 'name')
    instructors = Instructor.objects.filter(organization=org, is_active=True).order_by('first_name', 'last_name')
    class_groups = ClassGroup.objects.filter(organization=org, is_active=True).select_related('modality').order_by('modality__name', 'name')
    clients = Person.objects.filter(organization=org, status='active').order_by('first_name', 'last_name')

    context = {
        'resources': resources,
        'modalities': modalities,
        'instructors': instructors,
        'class_groups': class_groups,
        'clients': clients,
        'current_user_is_admin': request.user.is_staff or request.user.is_superuser,
    }

    return render(request, 'core/gantt_dynamic.html', context)


@login_required
def gantt_data(request):
    """API endpoint para dados do Gantt com otimizações."""
    org = request.organization
    date_param = request.GET.get('date')

    try:
        if date_param:
            selected_date = datetime.fromisoformat(date_param.replace('Z', '')).date()
        else:
            selected_date = timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    # Calcular início e fim do dia
    start_datetime = timezone.make_aware(datetime.combine(selected_date, datetime.min.time()))
    end_datetime = start_datetime + timedelta(days=1)

    # Obter eventos do dia com otimizações
    events = Event.objects.filter(
        organization=org,
        starts_at__gte=start_datetime,
        starts_at__lt=end_datetime
    ).select_related(
        'resource', 'modality', 'instructor', 'class_group', 'individual_client'
    ).annotate(
        bookings_count=Count('bookings', filter=Q(bookings__status='confirmed'))
    ).order_by('starts_at')

    # Serializar eventos para o Gantt
    events_data = []
    for event in events:
        events_data.append({
            'id': event.id,
            'title': event.display_title,
            'resource_id': event.resource.id,
            'resource_name': event.resource.name,
            'start_time': event.starts_at.strftime('%H:%M'),
            'end_time': event.ends_at.strftime('%H:%M'),
            'start_hour': event.starts_at.hour,
            'end_hour': event.ends_at.hour,
            'duration_minutes': int((event.ends_at - event.starts_at).total_seconds() / 60),
            'modality': {
                'id': event.modality.id if event.modality else None,
                'name': event.modality.name if event.modality else None,
                'color': event.modality.color if event.modality else '#6c757d'
            },
            'instructor': {
                'id': event.instructor.id if event.instructor else None,
                'name': event.instructor.full_name if event.instructor else 'Sem instrutor'
            },
            'event_type': event.event_type,
            'capacity': event.capacity,
            'bookings_count': event.bookings_count,
            'is_full': event.bookings_count >= event.capacity,
            'class_group': {
                'id': event.class_group.id if event.class_group else None,
                'name': event.class_group.name if event.class_group else None
            } if event.event_type == 'group_class' else None,
            'individual_client': {
                'id': event.individual_client.id if event.individual_client else None,
                'name': event.individual_client.full_name if event.individual_client else None
            } if event.event_type == 'individual' else None
        })

    # Obter recursos disponíveis
    resources_data = []
    for resource in Resource.objects.filter(organization=org, is_available=True).order_by('entity_type', 'name'):
        resources_data.append({
            'id': resource.id,
            'name': resource.name,
            'entity_type': resource.entity_type,
            'capacity': resource.capacity,
            'description': resource.description
        })

    return JsonResponse({
        'events': events_data,
        'resources': resources_data,
        'date': selected_date.isoformat(),
        'current_time': timezone.now().strftime('%H:%M')
    })


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def create_event_from_gantt(request):
    """Criar evento a partir do drag & drop no Gantt."""
    try:
        data = json.loads(request.body)
        org = request.organization

        # Validar dados obrigatórios
        resource_id = data.get('resource_id')
        start_time = data.get('start_time')  # formato: 'HH:MM'
        end_time = data.get('end_time')      # formato: 'HH:MM'
        date_str = data.get('date')          # formato: 'YYYY-MM-DD'

        if not all([resource_id, start_time, end_time, date_str]):
            return JsonResponse({'error': 'Dados obrigatórios em falta'}, status=400)

        # Validar recurso
        try:
            resource = Resource.objects.get(id=resource_id, organization=org)
        except Resource.DoesNotExist:
            return JsonResponse({'error': 'Recurso não encontrado'}, status=404)

        # Parsear data e horas
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_hour, start_minute = map(int, start_time.split(':'))
            end_hour, end_minute = map(int, end_time.split(':'))

            starts_at = timezone.make_aware(datetime.combine(event_date, datetime.min.time().replace(hour=start_hour, minute=start_minute)))
            ends_at = timezone.make_aware(datetime.combine(event_date, datetime.min.time().replace(hour=end_hour, minute=end_minute)))

        except ValueError as e:
            return JsonResponse({'error': f'Formato de data/hora inválido: {str(e)}'}, status=400)

        # Validar que end > start
        if ends_at <= starts_at:
            return JsonResponse({'error': 'Hora de fim deve ser posterior à hora de início'}, status=400)

        # Verificar conflitos
        conflicting_events = Event.objects.filter(
            organization=org,
            resource=resource,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at
        )

        if conflicting_events.exists():
            return JsonResponse({'error': 'Já existe um evento neste horário e espaço'}, status=400)

        # Criar evento preliminar
        event = Event(
            organization=org,
            resource=resource,
            title=f"Nova Aula - {resource.name}",
            starts_at=starts_at,
            ends_at=ends_at,
            capacity=resource.capacity,
            event_type=Event.EventType.OPEN_CLASS
        )

        # Se o utilizador não é admin, atribuir como instrutor
        if not (request.user.is_staff or request.user.is_superuser):
            try:
                instructor = Instructor.objects.get(organization=org, email=request.user.email)
                event.instructor = instructor
            except Instructor.DoesNotExist:
                pass

        event.save()

        return JsonResponse({
            'success': True,
            'event_id': event.id,
            'message': 'Evento criado com sucesso. Configure os detalhes no formulário.'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def update_event_details(request):
    """Atualizar detalhes do evento após criação no Gantt."""
    try:
        data = json.loads(request.body)
        org = request.organization

        event_id = data.get('event_id')
        if not event_id:
            return JsonResponse({'error': 'ID do evento obrigatório'}, status=400)

        try:
            event = Event.objects.get(id=event_id, organization=org)
        except Event.DoesNotExist:
            return JsonResponse({'error': 'Evento não encontrado'}, status=404)

        # Atualizar campos permitidos
        if 'title' in data:
            event.title = data['title']

        if 'description' in data:
            event.description = data['description']

        if 'modality_id' in data and data['modality_id']:
            try:
                modality = Modality.objects.get(id=data['modality_id'], organization=org)
                event.modality = modality
            except Modality.DoesNotExist:
                return JsonResponse({'error': 'Modalidade não encontrada'}, status=404)

        if 'instructor_id' in data and data['instructor_id']:
            try:
                instructor = Instructor.objects.get(id=data['instructor_id'], organization=org)
                event.instructor = instructor
            except Instructor.DoesNotExist:
                return JsonResponse({'error': 'Instrutor não encontrado'}, status=404)

        if 'event_type' in data:
            event.event_type = data['event_type']

            # Configurar campos específicos por tipo
            if event.event_type == Event.EventType.GROUP_CLASS:
                if 'class_group_id' in data and data['class_group_id']:
                    try:
                        class_group = ClassGroup.objects.get(id=data['class_group_id'], organization=org)
                        event.class_group = class_group
                        event.capacity = class_group.max_students
                        event.individual_client = None
                    except ClassGroup.DoesNotExist:
                        return JsonResponse({'error': 'Turma não encontrada'}, status=404)

            elif event.event_type == Event.EventType.INDIVIDUAL:
                if 'individual_client_id' in data and data['individual_client_id']:
                    try:
                        client = Person.objects.get(id=data['individual_client_id'], organization=org)
                        event.individual_client = client
                        event.capacity = 1
                        event.class_group = None
                    except Person.DoesNotExist:
                        return JsonResponse({'error': 'Cliente não encontrado'}, status=404)

            else:  # OPEN_CLASS
                event.class_group = None
                event.individual_client = None
                if 'capacity' in data:
                    event.capacity = min(int(data['capacity']), event.resource.capacity)

        event.save()

        return JsonResponse({
            'success': True,
            'message': 'Evento atualizado com sucesso',
            'event': {
                'id': event.id,
                'title': event.display_title,
                'modality_color': event.modality.color if event.modality else '#6c757d'
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)


@login_required
def get_event_details(request, event_id):
    """Obter detalhes de um evento para edição."""
    try:
        org = request.organization
        event = Event.objects.select_related(
            'resource', 'modality', 'instructor', 'class_group', 'individual_client'
        ).get(id=event_id, organization=org)

        return JsonResponse({
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'event_type': event.event_type,
            'modality_id': event.modality.id if event.modality else None,
            'instructor_id': event.instructor.id if event.instructor else None,
            'class_group_id': event.class_group.id if event.class_group else None,
            'individual_client_id': event.individual_client.id if event.individual_client else None,
            'capacity': event.capacity,
            'resource_id': event.resource.id,
            'starts_at': event.starts_at.isoformat(),
            'ends_at': event.ends_at.isoformat()
        })

    except Event.DoesNotExist:
        return JsonResponse({'error': 'Evento não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# CLASSE DE APIs OTIMIZADAS
class OptimizedGanttAPI:
    """API otimizada para operações do Gantt com cache inteligente."""

    @staticmethod
    @login_required
    def gantt_resources(request):
        """Lista otimizada de recursos para o Gantt."""
        org = request.organization

        resources = Resource.objects.filter(
            organization=org,
            is_available=True
        ).only(
            'id', 'name', 'capacity', 'entity_type', 'description'
        ).order_by('entity_type', 'name')

        data = [{
            'id': r.id,
            'name': r.name,
            'capacity': r.capacity,
            'entity_type': r.entity_type,
            'entity_display': r.get_entity_type_display(),
            'description': r.description[:100] if r.description else ''
        } for r in resources]

        return JsonResponse({
            'resources': data,
            'total_count': len(data),
            'cache_timestamp': timezone.now().isoformat()
        })

    @staticmethod
    @login_required
    def gantt_events_fast(request):
        """API ultra-rápida para eventos do Gantt."""
        org = request.organization

        # Parâmetros de filtro
        date_param = request.GET.get('date')
        resource_ids = request.GET.get('resources', '').split(',') if request.GET.get('resources') else []

        # Data selecionada
        try:
            if date_param:
                selected_date = datetime.fromisoformat(date_param.replace('Z', '')).date()
            else:
                selected_date = timezone.now().date()
        except ValueError:
            selected_date = timezone.now().date()

        # Query otimizada
        start_datetime = timezone.make_aware(datetime.combine(selected_date, datetime.min.time()))
        end_datetime = start_datetime + timedelta(days=1)

        events_query = Event.objects.filter(
            organization=org,
            starts_at__gte=start_datetime,
            starts_at__lt=end_datetime
        ).select_related(
            'resource', 'modality', 'instructor', 'class_group', 'individual_client'
        ).annotate(
            bookings_count=Count('bookings', filter=Q(bookings__status='confirmed'))
        )

        # Filtro por recursos se especificado
        if resource_ids and resource_ids[0]:
            try:
                resource_ids = [int(id) for id in resource_ids if id.isdigit()]
                events_query = events_query.filter(resource_id__in=resource_ids)
            except ValueError:
                pass

        events = events_query.order_by('starts_at')[:500]

        # Serialização otimizada
        events_data = []
        for event in events:
            start_hour = event.starts_at.hour
            duration_minutes = int((event.ends_at - event.starts_at).total_seconds() / 60)

            event_data = {
                'id': event.id,
                'title': event.display_title,
                'resource_id': event.resource_id,
                'start_hour': start_hour,
                'duration_minutes': duration_minutes,
                'start_time': event.starts_at.strftime('%H:%M'),
                'end_time': event.ends_at.strftime('%H:%M'),
                'event_type': event.event_type,
                'capacity': event.capacity,
                'bookings_count': event.bookings_count,

                'modality': {
                    'id': event.modality.id if event.modality else None,
                    'name': event.modality.name if event.modality else None,
                    'color': event.modality.color if event.modality else '#6c757d'
                },

                'instructor': {
                    'id': event.instructor.id if event.instructor else None,
                    'name': event.instructor.full_name if event.instructor else 'Sem instrutor'
                },

                'class_group': {
                    'id': event.class_group.id if event.class_group else None,
                    'name': event.class_group.name if event.class_group else None
                } if event.event_type == 'group_class' else None,

                'individual_client': {
                    'id': event.individual_client.id if event.individual_client else None,
                    'name': event.individual_client.full_name if event.individual_client else None
                } if event.event_type == 'individual' else None
            }

            events_data.append(event_data)

        return JsonResponse({
            'events': events_data,
            'date': selected_date.isoformat(),
            'current_time': timezone.now().strftime('%H:%M'),
            'total_events': len(events_data)
        })

    @staticmethod
    @login_required
    def gantt_create_event(request):
        """API otimizada para criação de eventos via drag & drop."""
        if request.method != 'POST':
            return JsonResponse({'error': 'Método não permitido'}, status=405)

        try:
            data = json.loads(request.body)
            org = request.organization

            # Validação básica
            required_fields = ['resource_id', 'start_time', 'end_time', 'date']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'error': f'Campo obrigatório: {field}'
                    }, status=400)

            # Validar recurso
            try:
                resource = Resource.objects.get(
                    id=data['resource_id'],
                    organization=org,
                    is_available=True
                )
            except Resource.DoesNotExist:
                return JsonResponse({
                    'error': 'Recurso não encontrado'
                }, status=404)

            # Parsear horários
            try:
                event_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                start_hour, start_minute = map(int, data['start_time'].split(':'))
                end_hour, end_minute = map(int, data['end_time'].split(':'))

                starts_at = timezone.make_aware(
                    datetime.combine(event_date, datetime.min.time().replace(
                        hour=start_hour, minute=start_minute
                    ))
                )
                ends_at = timezone.make_aware(
                    datetime.combine(event_date, datetime.min.time().replace(
                        hour=end_hour, minute=end_minute
                    ))
                )

            except ValueError as e:
                return JsonResponse({
                    'error': f'Formato inválido: {str(e)}'
                }, status=400)

            # Validar duração
            if ends_at <= starts_at:
                return JsonResponse({
                    'error': 'Hora de fim deve ser posterior'
                }, status=400)

            # Verificar conflitos
            conflicting_events = Event.objects.filter(
                organization=org,
                resource=resource,
                starts_at__lt=ends_at,
                ends_at__gt=starts_at
            ).exists()

            if conflicting_events:
                return JsonResponse({
                    'error': 'Conflito de horário'
                }, status=409)

            # Criar evento
            event = Event.objects.create(
                organization=org,
                resource=resource,
                title=f"Nova Aula - {resource.name}",
                starts_at=starts_at,
                ends_at=ends_at,
                capacity=resource.capacity,
                event_type=Event.EventType.OPEN_CLASS
            )

            # Atribuir instrutor se aplicável
            if not (request.user.is_staff or request.user.is_superuser):
                try:
                    instructor = Instructor.objects.get(
                        organization=org,
                        email=request.user.email,
                        is_active=True
                    )
                    event.instructor = instructor
                    event.save(update_fields=['instructor'])
                except Instructor.DoesNotExist:
                    pass

            return JsonResponse({
                'success': True,
                'event_id': event.id,
                'message': 'Evento criado com sucesso'
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Erro: {str(e)}'}, status=500)


# APIs auxiliares
@login_required
def get_form_data(request):
    """API para dados de formulários."""
    org = request.organization

    data = {
        'modalities': [{
            'id': m.id,
            'name': m.name,
            'entity_type': m.entity_type,
            'color': m.color
        } for m in Modality.objects.filter(organization=org, is_active=True)],

        'instructors': [{
            'id': i.id,
            'name': i.full_name,
            'entity_affiliation': i.entity_affiliation
        } for i in Instructor.objects.filter(organization=org, is_active=True)],

        'class_groups': [{
            'id': g.id,
            'name': g.name,
            'modality_name': g.modality.name,
            'max_students': g.max_students
        } for g in ClassGroup.objects.filter(organization=org, is_active=True).select_related('modality')],

        'clients': [{
            'id': p.id,
            'name': p.full_name,
            'entity_affiliation': p.entity_affiliation
        } for p in Person.objects.filter(organization=org, status='active')[:100]]
    }

    return JsonResponse(data)


@csrf_exempt
@login_required
def validate_event_conflict(request):
    """API para validar conflitos de eventos."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    try:
        data = json.loads(request.body)
        org = request.organization

        resource_id = data.get('resource_id')
        starts_at = datetime.fromisoformat(data.get('starts_at'))
        ends_at = datetime.fromisoformat(data.get('ends_at'))
        event_id = data.get('event_id')

        query = Event.objects.filter(
            organization=org,
            resource_id=resource_id,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at
        )

        if event_id:
            query = query.exclude(id=event_id)

        conflicts = query.select_related('instructor', 'modality').values(
            'id', 'title', 'starts_at', 'ends_at',
            'instructor__first_name', 'modality__name'
        )

        return JsonResponse({
            'has_conflicts': conflicts.exists(),
            'conflicts': list(conflicts)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# Booking APIs (placeholder para futuras implementações)
@login_required
def book_event(request, event_id):
    """API para reservar evento."""
    return JsonResponse({'message': 'Booking API - em desenvolvimento'})


@login_required
def cancel_booking(request, booking_id):
    """API para cancelar reserva."""
    return JsonResponse({'message': 'Cancel booking API - em desenvolvimento'})

