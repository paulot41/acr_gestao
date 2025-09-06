"""
APIs otimizadas para o sistema ACR Gestão.
Foco em performance, cache e validações robustas.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import (
    Event, Resource, Modality, Instructor, Person,
    ClassGroup, Booking, Organization
)
from .serializers import EventSerializer, ResourceSerializer


class OptimizedGanttAPI:
    """API otimizada para operações do Gantt com cache inteligente."""

    @staticmethod
    @login_required
    @cache_page(60)  # Cache por 1 minuto
    @vary_on_headers('X-Organization-Domain')
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
        """API ultra-rápida para eventos do Gantt com otimizações avançadas."""
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

        # Query otimizada com select_related e prefetch_related
        start_datetime = timezone.make_aware(datetime.combine(selected_date, datetime.min.time()))
        end_datetime = start_datetime + timedelta(days=1)

        events_query = Event.objects.filter(
            organization=org,
            starts_at__gte=start_datetime,
            starts_at__lt=end_datetime
        ).select_related(
            'resource', 'modality', 'instructor', 'class_group', 'individual_client'
        ).prefetch_related(
            Prefetch('bookings', queryset=Booking.objects.filter(status='confirmed'))
        )

        # Filtro por recursos se especificado
        if resource_ids and resource_ids[0]:  # Verificar se não está vazio
            try:
                resource_ids = [int(id) for id in resource_ids if id.isdigit()]
                events_query = events_query.filter(resource_id__in=resource_ids)
            except ValueError:
                pass

        # Limitar a 500 eventos para performance
        events = events_query.order_by('starts_at')[:500]

        # Serialização otimizada
        events_data = []
        for event in events:
            # Calcular posição no grid (em pixels, assumindo 80px por hora)
            start_hour = event.starts_at.hour
            start_minute = event.starts_at.minute
            duration_minutes = int((event.ends_at - event.starts_at).total_seconds() / 60)

            # Dados essenciais para o frontend
            event_data = {
                'id': event.id,
                'title': event.display_title,
                'resource_id': event.resource_id,
                'start_hour': start_hour,
                'start_minute': start_minute,
                'duration_minutes': duration_minutes,
                'start_time': event.starts_at.strftime('%H:%M'),
                'end_time': event.ends_at.strftime('%H:%M'),
                'event_type': event.event_type,
                'capacity': event.capacity,
                'bookings_count': len(event.bookings.all()) if hasattr(event, 'bookings') else 0,

                # Dados da modalidade
                'modality': {
                    'id': event.modality.id if event.modality else None,
                    'name': event.modality.name if event.modality else None,
                    'color': event.modality.color if event.modality else '#6c757d'
                },

                # Dados do instrutor
                'instructor': {
                    'id': event.instructor.id if event.instructor else None,
                    'name': event.instructor.full_name if event.instructor else 'Sem instrutor'
                },

                # Dados específicos por tipo
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
            'total_events': len(events_data),
            'query_time': timezone.now().isoformat()
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

            # Validação de dados obrigatórios
            required_fields = ['resource_id', 'start_time', 'end_time', 'date']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'error': f'Campo obrigatório em falta: {field}'
                    }, status=400)

            # Validar e obter recurso
            try:
                resource = Resource.objects.get(
                    id=data['resource_id'],
                    organization=org,
                    is_available=True
                )
            except Resource.DoesNotExist:
                return JsonResponse({
                    'error': 'Recurso não encontrado ou indisponível'
                }, status=404)

            # Parsear e validar horários
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

            except (ValueError, TypeError) as e:
                return JsonResponse({
                    'error': f'Formato de data/hora inválido: {str(e)}'
                }, status=400)

            # Validar duração mínima (15 minutos)
            if (ends_at - starts_at).total_seconds() < 900:  # 15 minutos
                return JsonResponse({
                    'error': 'Duração mínima de 15 minutos'
                }, status=400)

            # Verificar conflitos de horário
            conflicting_events = Event.objects.filter(
                organization=org,
                resource=resource,
                starts_at__lt=ends_at,
                ends_at__gt=starts_at
            ).exists()

            if conflicting_events:
                return JsonResponse({
                    'error': 'Já existe um evento neste horário e espaço'
                }, status=409)  # Conflict

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

            # Atribuir instrutor se não é admin
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
                'message': 'Evento criado com sucesso',
                'event': {
                    'id': event.id,
                    'title': event.title,
                    'start_time': event.starts_at.strftime('%H:%M'),
                    'end_time': event.ends_at.strftime('%H:%M'),
                    'resource_name': resource.name
                }
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Erro interno: {str(e)}'
            }, status=500)


# APIs para dados de formulários
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_form_data(request):
    """API para obter dados necessários para formulários do sistema."""
    org = request.organization

    # Cache para dados que não mudam frequentemente
    cache_key = f"form_data_{org.id}"

    data = {
        'modalities': [
            {
                'id': m.id,
                'name': m.name,
                'entity_type': m.entity_type,
                'entity_display': m.get_entity_type_display(),
                'color': m.color,
                'duration': m.default_duration_minutes
            }
            for m in Modality.objects.filter(organization=org, is_active=True)
        ],

        'instructors': [
            {
                'id': i.id,
                'name': i.full_name,
                'entity_affiliation': i.entity_affiliation,
                'entity_display': i.get_entity_affiliation_display(),
                'specialties': i.specialties
            }
            for i in Instructor.objects.filter(organization=org, is_active=True)
        ],

        'class_groups': [
            {
                'id': g.id,
                'name': g.name,
                'modality_name': g.modality.name,
                'max_students': g.max_students,
                'current_members': g.current_members_count,
                'level': g.level
            }
            for g in ClassGroup.objects.filter(organization=org, is_active=True).select_related('modality')
        ],

        'clients': [
            {
                'id': p.id,
                'name': p.full_name,
                'entity_affiliation': p.entity_affiliation,
                'entity_display': p.get_entity_affiliation_display(),
                'email': p.email
            }
            for p in Person.objects.filter(organization=org, status='active')[:100]  # Limitar para performance
        ],

        'resources': [
            {
                'id': r.id,
                'name': r.name,
                'capacity': r.capacity,
                'entity_type': r.entity_type,
                'entity_display': r.get_entity_type_display()
            }
            for r in Resource.objects.filter(organization=org, is_available=True)
        ]
    }

    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def validate_event_conflict(request):
    """API para validar conflitos de eventos antes da criação."""
    data = request.data
    org = request.organization

    try:
        resource_id = data.get('resource_id')
        starts_at = datetime.fromisoformat(data.get('starts_at'))
        ends_at = datetime.fromisoformat(data.get('ends_at'))
        event_id = data.get('event_id')  # Para edição

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
            'instructor__first_name', 'instructor__last_name',
            'modality__name'
        )

        return Response({
            'has_conflicts': conflicts.exists(),
            'conflicts': list(conflicts),
            'total_conflicts': conflicts.count()
        })

    except (ValueError, TypeError) as e:
        return Response({
            'error': f'Dados inválidos: {str(e)}'
        }, status=400)
