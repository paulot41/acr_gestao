from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta
import json
import logging
from django.db import IntegrityError, DatabaseError
from django.core.exceptions import ValidationError
from django.urls import reverse
from .auth_views import role_required
from .services.bookings import cancel_booking
from .services.scheduling import create_recurring_event_series
from .models import Person, Event, Booking, Resource, Modality, Instructor, ClassGroup

logger = logging.getLogger(__name__)


# NOVOS ENDPOINTS PARA GANTT DINÂMICO

@role_required(["admin", "staff", "instructor"])
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


@role_required(["admin", "staff", "instructor"])
def gantt_data(request):
    """API endpoint para dados do Gantt com suporte a vista diária ou semanal e filtros."""
    org = request.organization
    date_param = request.GET.get('date')
    view_type = request.GET.get('view_type', request.GET.get('view', 'day'))  # 'day' ou 'week'

    try:
        if date_param:
            selected_date = datetime.fromisoformat(date_param.replace('Z', '')).date()
        else:
            selected_date = timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    if view_type == 'week':
        # Segunda-feira da semana de selected_date até Domingo
        week_start = selected_date - timedelta(days=selected_date.weekday())
        week_end = week_start + timedelta(days=6)
        start_datetime = timezone.make_aware(datetime.combine(week_start, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(week_end + timedelta(days=1), datetime.min.time()))
    else:
        week_start = selected_date
        week_end = selected_date
        start_datetime = timezone.make_aware(datetime.combine(selected_date, datetime.min.time()))
        end_datetime = start_datetime + timedelta(days=1)

    # Obter eventos com otimizações
    events_qs = Event.objects.filter(
        organization=org,
        starts_at__gte=start_datetime,
        starts_at__lt=end_datetime
    )

    # Filtros opcionais
    resource_id = request.GET.get('resource_id')
    if resource_id and resource_id.isdigit():
        events_qs = events_qs.filter(resource_id=int(resource_id))

    modality_id = request.GET.get('modality_id')
    if modality_id and modality_id.isdigit():
        events_qs = events_qs.filter(modality_id=int(modality_id))

    instructor_id = request.GET.get('instructor_id')
    if instructor_id and instructor_id.isdigit():
        events_qs = events_qs.filter(instructor_id=int(instructor_id))

    events = events_qs.select_related(
        'resource', 'modality', 'instructor', 'class_group', 'individual_client'
    ).annotate(
        confirmed_bookings_count=Count('bookings', filter=Q(bookings__status=Booking.Status.CONFIRMED))
    ).order_by('starts_at')

    # Serializar eventos para o Gantt
    events_data = []
    for event in events:
        cap = event.capacity or (event.resource.capacity if event.resource else 0)
        confirmed = event.confirmed_bookings_count
        occ_pct = round((confirmed / cap * 100) if cap else 0, 1)
        checkin_url = reverse('core:event_checkin', kwargs={'event_id': event.id})

        events_data.append({
            'id': event.id,
            'title': event.display_title,
            'resource_id': event.resource.id,
            'resource_name': event.resource.name,
            'date': event.starts_at.date().isoformat(),
            'weekday': event.starts_at.weekday(),  # 0=Segunda, ..., 6=Domingo
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
            'capacity': cap,
            'bookings_count': confirmed,
            'occupancy_pct': occ_pct,
            'is_full': confirmed >= cap if cap else False,
            'recurrence_group_id': str(event.recurrence_group_id) if event.recurrence_group_id else None,
            'is_recurring': bool(event.recurrence_group_id),
            'checkin_url': checkin_url,
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
        'view_type': view_type,
        'week_start': week_start.isoformat(),
        'week_end': week_end.isoformat(),
        'current_time': timezone.now().strftime('%H:%M')
    })


@role_required(["admin", "staff", "instructor"])
@require_http_methods(["POST"])
def create_event_from_gantt(request):
    """Criar evento ou série recorrente a partir do Gantt."""
    try:
        data = json.loads(request.body)
        org = request.organization

        # Validar dados obrigatórios
        resource_id = data.get('resource_id')
        start_time = data.get('start_time')  # formato: 'HH:MM'
        end_time = data.get('end_time')      # formato: 'HH:MM'
        date_str = data.get('date')          # formato: 'YYYY-MM-DD'
        is_recurring = bool(data.get('is_recurring', False))

        if not all([resource_id, start_time, end_time, date_str]):
            return JsonResponse({'error': 'Dados obrigatórios em falta (espaço, horário e data)'}, status=400)

        # Validar recurso
        try:
            resource = Resource.objects.get(id=resource_id, organization=org)
        except Resource.DoesNotExist:
            return JsonResponse({'error': 'Recurso não encontrado'}, status=404)

        # Parsear data
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError as e:
            return JsonResponse({'error': f'Formato de data inválido: {str(e)}'}, status=400)

        # Determinar instrutor se especificado ou atribuir padrão
        instructor = None
        instructor_id = data.get('instructor_id')
        if instructor_id:
            try:
                instructor = Instructor.objects.get(id=instructor_id, organization=org)
            except Instructor.DoesNotExist:
                return JsonResponse({'error': 'Instrutor não encontrado'}, status=404)
        elif not (request.user.is_staff or request.user.is_superuser):
            try:
                instructor = Instructor.objects.get(organization=org, email=request.user.email)
            except Instructor.DoesNotExist:
                pass

        # Modalidade
        modality = None
        modality_id = data.get('modality_id')
        if modality_id:
            try:
                modality = Modality.objects.get(id=modality_id, organization=org)
            except Modality.DoesNotExist:
                return JsonResponse({'error': 'Modalidade não encontrada'}, status=404)

        # Turma
        class_group = None
        class_group_id = data.get('class_group_id')
        if class_group_id:
            try:
                class_group = ClassGroup.objects.get(id=class_group_id, organization=org)
            except ClassGroup.DoesNotExist:
                return JsonResponse({'error': 'Turma não encontrada'}, status=404)

        # Cliente individual
        individual_client = None
        individual_client_id = data.get('individual_client_id')
        if individual_client_id:
            try:
                individual_client = Person.objects.get(id=individual_client_id, organization=org)
            except Person.DoesNotExist:
                return JsonResponse({'error': 'Cliente não encontrado'}, status=404)

        event_type = data.get('event_type', Event.EventType.OPEN_CLASS)
        title = (data.get('title') or '').strip() or f"Aula - {resource.name}"
        description = data.get('description', '')
        capacity = int(data.get('capacity')) if data.get('capacity') else None

        # CASO 1: Série Recorrente
        if is_recurring:
            recurrence_end_str = data.get('recurrence_end_date')
            weekdays = data.get('recurrence_weekdays', [])

            if not recurrence_end_str:
                return JsonResponse({'error': 'Data final da série recorrente é obrigatória.'}, status=400)

            try:
                rec_end_date = datetime.strptime(recurrence_end_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Formato da data final da série inválido (YYYY-MM-DD).'}, status=400)

            if not weekdays or not isinstance(weekdays, list):
                # Se não especificado explicitamente, usa o dia da semana do evento inicial
                weekdays = [event_date.weekday()]
            else:
                weekdays = [int(w) for w in weekdays]

            series_result = create_recurring_event_series(
                organization=org,
                resource=resource,
                start_time=start_time,
                end_time=end_time,
                start_date=event_date,
                end_date=rec_end_date,
                weekdays=weekdays,
                title=title,
                event_type=event_type,
                capacity=capacity,
                description=description,
                modality=modality,
                instructor=instructor,
                class_group=class_group,
                individual_client=individual_client,
            )

            if series_result['created_count'] == 0:
                reasons = "; ".join([d['reason'] for d in series_result['skipped_dates'][:3]])
                return JsonResponse({
                    'error': f"Não foi possível criar nenhuma aula na série devido a conflitos: {reasons}"
                }, status=400)

            msg = f"Série criada: {series_result['created_count']} aulas agendadas com sucesso."
            if series_result['skipped_count'] > 0:
                msg += f" ({series_result['skipped_count']} ocorrências ignoradas devido a conflitos pré-existentes)."

            return JsonResponse({
                'success': True,
                'is_recurring': True,
                'recurrence_group_id': series_result['recurrence_group_id'],
                'created_count': series_result['created_count'],
                'created_ids': series_result['created_ids'],
                'skipped_count': series_result['skipped_count'],
                'skipped_dates': series_result['skipped_dates'],
                'event_id': series_result['created_ids'][0] if series_result['created_ids'] else None,
                'message': msg
            })

        # CASO 2: Evento Individual
        try:
            start_hour, start_minute = map(int, start_time.split(':')[:2])
            end_hour, end_minute = map(int, end_time.split(':')[:2])

            starts_at = timezone.make_aware(datetime.combine(event_date, datetime.min.time().replace(hour=start_hour, minute=start_minute)))
            ends_at = timezone.make_aware(datetime.combine(event_date, datetime.min.time().replace(hour=end_hour, minute=end_minute)))

        except ValueError as e:
            return JsonResponse({'error': f'Formato de hora inválido: {str(e)}'}, status=400)

        if ends_at <= starts_at:
            return JsonResponse({'error': 'Hora de fim deve ser posterior à hora de início'}, status=400)

        # Criar evento
        event = Event(
            organization=org,
            resource=resource,
            modality=modality,
            instructor=instructor,
            title=title,
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
            event_type=event_type,
            capacity=capacity or resource.capacity,
            class_group=class_group,
            individual_client=individual_client,
        )

        event.clean()
        event.save()

        return JsonResponse({
            'success': True,
            'is_recurring': False,
            'event_id': event.id,
            'message': 'Aula agendada com sucesso.'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except ValidationError as e:
        msg = e.messages[0] if hasattr(e, 'messages') and e.messages else str(e)
        return JsonResponse({'error': msg}, status=400)
    except IntegrityError as e:
        logger.error("Erro ao criar evento: %s", e)
        return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)


@role_required(["admin", "staff", "instructor"])
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

        if 'instructor_id' in data:
            if data['instructor_id']:
                try:
                    instructor = Instructor.objects.get(id=data['instructor_id'], organization=org)
                    event.instructor = instructor
                except Instructor.DoesNotExist:
                    return JsonResponse({'error': 'Instrutor não encontrado'}, status=404)
            else:
                event.instructor = None

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

        # Atualização opcional de horários e recurso (suporta drag no Gantt)
        # Aceita: 'date' (YYYY-MM-DD), 'start_time' (HH:MM), 'end_time' (HH:MM), 'resource_id'
        date_str = data.get('date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        resource_id = data.get('resource_id')

        if any([date_str, start_time, end_time, resource_id]):
            # Usar valores atuais como defaults
            event_date = event.starts_at.date()
            if date_str:
                try:
                    event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'error': 'Data inválida'}, status=400)

            # Parse horas
            start_hour = event.starts_at.hour
            start_minute = event.starts_at.minute
            end_hour = event.ends_at.hour
            end_minute = event.ends_at.minute

            if start_time:
                try:
                    parts = start_time.split(':')
                    start_hour, start_minute = int(parts[0]), int(parts[1])
                except Exception:
                    return JsonResponse({'error': 'Hora inicial inválida'}, status=400)
            if end_time:
                try:
                    parts = end_time.split(':')
                    end_hour, end_minute = int(parts[0]), int(parts[1])
                except Exception:
                    return JsonResponse({'error': 'Hora final inválida'}, status=400)

            new_starts_at = timezone.make_aware(datetime.combine(event_date, datetime.min.time().replace(hour=start_hour, minute=start_minute)))
            new_ends_at = timezone.make_aware(datetime.combine(event_date, datetime.min.time().replace(hour=end_hour, minute=end_minute)))

            if new_ends_at <= new_starts_at:
                return JsonResponse({'error': 'Hora de fim deve ser posterior à hora de início'}, status=400)

            # Mudar recurso se necessário
            if resource_id:
                try:
                    new_resource = Resource.objects.get(id=resource_id, organization=org)
                except Resource.DoesNotExist:
                    return JsonResponse({'error': 'Recurso não encontrado'}, status=404)
            else:
                new_resource = event.resource

            event.resource = new_resource
            event.starts_at = new_starts_at
            event.ends_at = new_ends_at

        # Verificar conflitos de espaço (excluir o próprio evento)
        conflict_qs = Event.objects.filter(
            organization=org,
            resource=event.resource,
            starts_at__lt=event.ends_at,
            ends_at__gt=event.starts_at
        ).exclude(id=event.id)

        if conflict_qs.exists():
            return JsonResponse({'error': 'Conflito de agenda no espaço selecionado'}, status=400)

        # Verificar conflito de instrutor (excluir o próprio evento)
        if event.instructor:
            inst_conflict_qs = Event.objects.filter(
                organization=org,
                instructor=event.instructor,
                starts_at__lt=event.ends_at,
                ends_at__gt=event.starts_at
            ).exclude(id=event.id)

            if inst_conflict_qs.exists():
                return JsonResponse({
                    'error': f'O instrutor {event.instructor.full_name} já tem uma aula agendada neste horário'
                }, status=400)

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
    except ValidationError as e:
        msg = e.messages[0] if hasattr(e, 'messages') and e.messages else str(e)
        return JsonResponse({'error': msg}, status=400)
    except IntegrityError as e:
        logger.error("Erro ao atualizar evento: %s", e)
        return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)


@role_required(["admin", "staff", "instructor"])
@require_http_methods(["POST"])
def delete_event_api(request):
    """Eliminar um evento ou série recorrente via API do Gantt."""
    try:
        data = json.loads(request.body)
        org = request.organization
        event_id = data.get('event_id')
        delete_series = bool(data.get('delete_series', False))

        if not event_id:
            return JsonResponse({'success': False, 'error': 'ID do evento obrigatório'}, status=400)

        try:
            event = Event.objects.get(id=event_id, organization=org)
        except Event.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Evento não encontrado'}, status=404)

        if delete_series and event.recurrence_group_id:
            deleted_count, _ = Event.objects.filter(
                organization=org,
                recurrence_group_id=event.recurrence_group_id
            ).delete()
            return JsonResponse({
                'success': True,
                'series_deleted': True,
                'count': deleted_count,
                'message': f'{deleted_count} aulas da série recorrente eliminadas com sucesso.'
            })

        event.delete()
        return JsonResponse({
            'success': True,
            'series_deleted': False,
            'message': 'Aula eliminada com sucesso.'
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except DatabaseError as e:
        logger.error("Erro ao eliminar evento: %s", e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@role_required(["admin", "staff", "instructor"])
def get_event_details(request, event_id):
    """Obter detalhes de um evento para visualização e edição."""
    try:
        org = request.organization
        event = Event.objects.select_related(
            'resource', 'modality', 'instructor', 'class_group', 'individual_client'
        ).get(id=event_id, organization=org)

        confirmed_count = event.bookings.filter(status=Booking.Status.CONFIRMED).count()
        eff_capacity = event.capacity or (event.resource.capacity if event.resource else 0)
        occupancy_pct = round((confirmed_count / eff_capacity * 100) if eff_capacity else 0, 1)

        return JsonResponse({
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'event_type': event.event_type,
            'modality_id': event.modality.id if event.modality else None,
            'modality_name': event.modality.name if event.modality else None,
            'instructor_id': event.instructor.id if event.instructor else None,
            'instructor_name': event.instructor.full_name if event.instructor else None,
            'class_group_id': event.class_group.id if event.class_group else None,
            'individual_client_id': event.individual_client.id if event.individual_client else None,
            'capacity': eff_capacity,
            'bookings_count': confirmed_count,
            'occupancy_pct': occupancy_pct,
            'resource_id': event.resource.id,
            'resource_name': event.resource.name,
            'starts_at': event.starts_at.isoformat(),
            'ends_at': event.ends_at.isoformat(),
            'start_time': event.starts_at.strftime('%H:%M'),
            'end_time': event.ends_at.strftime('%H:%M'),
            'date': event.starts_at.date().isoformat(),
            'recurrence_group_id': str(event.recurrence_group_id) if event.recurrence_group_id else None,
            'is_recurring': bool(event.recurrence_group_id),
            'checkin_url': reverse('core:event_checkin', kwargs={'event_id': event.id})
        })

    except Event.DoesNotExist:
        return JsonResponse({'error': 'Evento não encontrado'}, status=404)
    except DatabaseError as e:
        logger.error("Erro ao obter detalhes do evento: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


# CLASSE DE APIs OTIMIZADAS
class OptimizedGanttAPI:
    """API otimizada para operações do Gantt com cache inteligente."""

    @staticmethod
    @role_required(["admin", "staff", "instructor"])
    def gantt_resources(request):
        """Lista otimizada de recursos para o Gantt."""
        org = request.organization

        cache_key = f"gantt:resources:{org.id}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse(cached)

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

        payload = {
            'resources': data,
            'total_count': len(data),
            'cache_timestamp': timezone.now().isoformat()
        }
        cache.set(cache_key, payload, timeout=300)
        return JsonResponse(payload)

    @staticmethod
    @role_required(["admin", "staff", "instructor"])
    def gantt_events_fast(request):
        """API ultra-rápida para eventos do Gantt."""
        org = request.organization

        # Parâmetros de filtro
        date_param = request.GET.get('date')
        resource_ids_param = request.GET.get('resources', '')
        resource_ids = [rid for rid in resource_ids_param.split(',') if rid] if resource_ids_param else []

        # Data selecionada
        try:
            if date_param:
                selected_date = datetime.fromisoformat(date_param.replace('Z', '')).date()
            else:
                selected_date = timezone.now().date()
        except ValueError:
            selected_date = timezone.now().date()

        resource_ids = sorted({int(rid) for rid in resource_ids if rid.isdigit()})
        resource_key = ",".join(str(rid) for rid in resource_ids) if resource_ids else "all"
        cache_key = f"gantt:events:{org.id}:{selected_date.isoformat()}:{resource_key}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse(cached)

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
            confirmed_bookings_count=Count('bookings', filter=Q(bookings__status=Booking.Status.CONFIRMED))
        )

        # Filtro por recursos se especificado
        if resource_ids:
            events_query = events_query.filter(resource_id__in=resource_ids)

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
                'bookings_count': event.confirmed_bookings_count,

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

        payload = {
            'events': events_data,
            'date': selected_date.isoformat(),
            'current_time': timezone.now().strftime('%H:%M'),
            'total_events': len(events_data)
        }
        cache.set(cache_key, payload, timeout=15)
        return JsonResponse(payload)

    @staticmethod
    @role_required(["admin", "staff", "instructor"])
    @require_http_methods(["POST"])
    def gantt_create_event(request):
        """Criar evento otimizado via API."""
        # Reutilizar lógica do create_event_from_gantt
        return create_event_from_gantt(request)


# API para dados auxiliares do formulário
@role_required(["admin", "staff", "instructor"])
def get_form_data(request):
    """Obter dados para formulários (modalities, instructors, etc.)."""
    org = request.organization

    modalities = Modality.objects.filter(organization=org, is_active=True).values('id', 'name', 'color', 'entity_type')
    instructors = Instructor.objects.filter(organization=org, is_active=True).values('id', 'first_name', 'last_name', 'email')
    class_groups = ClassGroup.objects.filter(organization=org, is_active=True).select_related('modality').values(
        'id', 'name', 'max_students', 'modality__name', 'modality_id'
    )
    clients = Person.objects.filter(organization=org, status='active').values('id', 'first_name', 'last_name', 'email')

    return JsonResponse({
        'modalities': list(modalities),
        'instructors': [
            {
                'id': i['id'],
                'full_name': f"{i['first_name']} {i['last_name']}",
                'email': i['email']
            } for i in instructors
        ],
        'class_groups': list(class_groups),
        'clients': [
            {
                'id': c['id'],
                'full_name': f"{c['first_name']} {c['last_name']}",
                'email': c['email']
            } for c in clients
        ]
    })


@role_required(["admin", "staff", "instructor"])
@require_http_methods(["POST"])
def validate_event_conflict(request):
    """Validar conflitos de eventos antes da criação."""
    try:
        data = json.loads(request.body)
        org = request.organization

        resource_id = data.get('resource_id')
        starts_at_str = data.get('starts_at')
        ends_at_str = data.get('ends_at')
        exclude_event_id = data.get('exclude_event_id')  # Para edições

        instructor_id = data.get('instructor_id')

        if not all([starts_at_str, ends_at_str]):
            return JsonResponse({'error': 'Dados obrigatórios em falta'}, status=400)

        if not resource_id and not instructor_id:
            return JsonResponse({'error': 'Recurso ou Instrutor obrigatório para validação'}, status=400)

        try:
            starts_at = datetime.fromisoformat(starts_at_str.replace('Z', ''))
            ends_at = datetime.fromisoformat(ends_at_str.replace('Z', ''))
            starts_at = timezone.make_aware(starts_at) if timezone.is_naive(starts_at) else starts_at
            ends_at = timezone.make_aware(ends_at) if timezone.is_naive(ends_at) else ends_at
        except ValueError:
            return JsonResponse({'error': 'Formato de data/hora inválido'}, status=400)

        if ends_at <= starts_at:
            return JsonResponse({'error': 'Hora de fim deve ser posterior à hora de início'}, status=400)

        # 1. Verificar conflitos de espaço/recurso
        if resource_id:
            conflicts = Event.objects.filter(
                organization=org,
                resource_id=resource_id,
                starts_at__lt=ends_at,
                ends_at__gt=starts_at
            )
            if exclude_event_id:
                conflicts = conflicts.exclude(id=exclude_event_id)

            if conflicts.exists():
                conflict_list = [
                    {
                        'id': c.id,
                        'title': c.title,
                        'starts_at': c.starts_at.isoformat(),
                        'ends_at': c.ends_at.isoformat()
                    } for c in conflicts
                ]
                return JsonResponse({
                    'has_conflict': True,
                    'conflict_type': 'resource',
                    'message': 'Já existe um evento neste horário e espaço',
                    'conflicts': conflict_list
                })

        # 2. Verificar conflitos de instrutor
        if instructor_id:
            inst_conflicts = Event.objects.filter(
                organization=org,
                instructor_id=instructor_id,
                starts_at__lt=ends_at,
                ends_at__gt=starts_at
            )
            if exclude_event_id:
                inst_conflicts = inst_conflicts.exclude(id=exclude_event_id)

            if inst_conflicts.exists():
                inst_conflict_list = [
                    {
                        'id': c.id,
                        'title': c.title,
                        'resource_name': c.resource.name if c.resource else '',
                        'starts_at': c.starts_at.isoformat(),
                        'ends_at': c.ends_at.isoformat()
                    } for c in inst_conflicts
                ]
                return JsonResponse({
                    'has_conflict': True,
                    'conflict_type': 'instructor',
                    'message': 'O instrutor já tem uma aula agendada neste horário',
                    'conflicts': inst_conflict_list
                })

        return JsonResponse({'has_conflict': False})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except DatabaseError as e:
        logger.error("Erro ao verificar conflitos de evento: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def cancel_booking_api(request, booking_id):
    """API para cancelar uma reserva de aula."""
    try:
        org = request.organization

        # Verificar se a reserva existe e pertence à organização
        try:
            booking = Booking.objects.get(id=booking_id, organization=org)
        except Booking.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Reserva não encontrada'
            }, status=404)

        result = cancel_booking(booking, request.user)
        return JsonResponse(
            {'success': result.ok, 'message': result.message},
            status=result.status_code,
        )

    except DatabaseError as e:
        logger.error("Erro ao cancelar reserva: %s", e)
        return JsonResponse({
            'success': False,
            'message': f'Erro ao cancelar reserva: {str(e)}'
        }, status=500)
