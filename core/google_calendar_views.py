"""
Views para integração Google Calendar.
Configura OAuth2, sincronização e gestão de calendários.
"""

import logging
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .auth_views import role_required
from django.http import JsonResponse, Http404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from googleapiclient.errors import HttpError

from .models import Organization, Instructor, Event, GoogleCalendarConfig, InstructorGoogleCalendar, GoogleCalendarSyncLog
from .services.google_calendar import get_google_calendar_service
from .middleware import get_current_organization

logger = logging.getLogger(__name__)


@role_required(["admin", "staff"])
def google_calendar_setup(request):
    """Página de configuração inicial do Google Calendar."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")

    try:
        config = GoogleCalendarConfig.objects.get(organization=organization)
    except GoogleCalendarConfig.DoesNotExist:
        config = GoogleCalendarConfig.objects.create(organization=organization)

    # Prefill credentials from environment if available and not yet set
    updated = False
    env_client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
    env_client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
    if env_client_id and not config.client_id:
        config.client_id = env_client_id
        updated = True
    if env_client_secret and not config.client_secret:
        config.client_secret = env_client_secret
        updated = True
    if updated:
        config.save(update_fields=['client_id', 'client_secret'])

    context = {
        'config': config,
        'organization': organization,
        'has_credentials': bool(config.client_id and config.client_secret),
        'is_authenticated': bool(config.access_token and config.is_token_valid),
        'last_sync': config.last_sync,
        'sync_enabled': config.sync_enabled
    }

    return render(request, 'core/google_calendar/setup.html', context)


@role_required(["admin", "staff"])
@require_http_methods(["POST"])
def google_calendar_save_credentials(request):
    """Guardar credenciais OAuth2 do Google."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")

    client_id = request.POST.get('client_id', '').strip()
    client_secret = request.POST.get('client_secret', '').strip()

    if not client_id or not client_secret:
        messages.error(request, "Client ID e Client Secret são obrigatórios.")
        return redirect('core:google_calendar_setup')

    try:
        config, created = GoogleCalendarConfig.objects.get_or_create(organization=organization)
        config.client_id = client_id
        config.client_secret = client_secret
        config.save()

        messages.success(request, "Credenciais Google guardadas com sucesso!")
        logger.info(f"Credenciais Google guardadas para {organization.name}")

    except (ValidationError, IntegrityError) as e:
        messages.error(request, f"Erro ao guardar credenciais: {e}")
        logger.error(f"Erro ao guardar credenciais Google para {organization.name}: {e}")

    return redirect('core:google_calendar_setup')


@role_required(["admin", "staff"])
def google_calendar_oauth_start(request):
    """Iniciar fluxo OAuth2 para autorização Google."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")

    try:
        service = get_google_calendar_service(organization)
        redirect_uri = request.build_absolute_uri(reverse('core:google_calendar_oauth_callback'))

        authorization_url, state = service.setup_oauth_flow(redirect_uri)

        # Guardar state na sessão para validação
        request.session['google_oauth_state'] = state

        return redirect(authorization_url)

    except ValidationError as e:
        messages.error(request, f"Erro na configuração OAuth: {e}")
        return redirect('core:google_calendar_setup')
    except HttpError as e:
        messages.error(request, f"Erro na comunicação com Google: {e}")
        logger.error(f"Erro ao iniciar OAuth para {organization.name}: {e}")
        return redirect('core:google_calendar_setup')


@role_required(["admin", "staff"])
def google_calendar_oauth_callback(request):
    """Callback OAuth2 - processar autorização do Google."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")

    # Verificar parâmetros
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')

    if error:
        messages.error(request, f"Autorização Google cancelada: {error}")
        return redirect('core:google_calendar_setup')

    if not code or not state:
        messages.error(request, "Parâmetros OAuth inválidos.")
        return redirect('core:google_calendar_setup')

    # Verificar state
    session_state = request.session.get('google_oauth_state')
    if state != session_state:
        messages.error(request, "Estado OAuth inválido. Tente novamente.")
        return redirect('core:google_calendar_setup')

    try:
        service = get_google_calendar_service(organization)
        redirect_uri = request.build_absolute_uri(reverse('core:google_calendar_oauth_callback'))

        service.complete_oauth_flow(code, redirect_uri, state)

        # Limpar state da sessão
        request.session.pop('google_oauth_state', None)

        messages.success(request, "Autorização Google Calendar configurada com sucesso!")
        logger.info(f"OAuth Google configurado para {organization.name}")

    except (ValidationError, HttpError) as e:
        messages.error(request, f"Erro ao completar autorização: {e}")
        logger.error(f"Erro no callback OAuth para {organization.name}: {e}")

    return redirect('core:google_calendar_setup')


@role_required(["admin", "staff"])
def google_calendar_instructors(request):
    """Página de gestão de calendários dos instrutores."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")

    # Verificar se a configuração está pronta
    try:
        config = GoogleCalendarConfig.objects.get(organization=organization)
        if not config.sync_enabled or not config.is_token_valid:
            messages.warning(request, "Configure primeiro a autorização Google Calendar.")
            return redirect('core:google_calendar_setup')
    except GoogleCalendarConfig.DoesNotExist:
        messages.error(request, "Configure primeiro o Google Calendar.")
        return redirect('core:google_calendar_setup')

    # Obter instrutores com suas configurações
    instructors = Instructor.objects.filter(organization=organization, is_active=True)

    instructor_configs = []
    for instructor in instructors:
        try:
            google_config = instructor.google_calendar
        except InstructorGoogleCalendar.DoesNotExist:
            google_config = None

        instructor_configs.append({
            'instructor': instructor,
            'google_config': google_config,
            'has_calendar': bool(google_config and google_config.google_calendar_id),
            'sync_enabled': bool(google_config and google_config.sync_enabled),
            'last_sync': google_config.last_sync if google_config else None
        })

    context = {
        'organization': organization,
        'instructor_configs': instructor_configs,
        'config': config
    }

    return render(request, 'core/google_calendar/instructors.html', context)


@role_required(["admin", "staff"])
@require_http_methods(["POST"])
def google_calendar_create_instructor_calendar(request, instructor_id):
    """Criar calendário Google para um instrutor específico."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")
    instructor = get_object_or_404(Instructor, id=instructor_id, organization=organization)

    try:
        service = get_google_calendar_service(organization)
        calendar_id = service.create_instructor_calendar(instructor)

        messages.success(request, f"Calendário criado para {instructor.full_name}!")
        logger.info(f"Calendário criado para {instructor.full_name}: {calendar_id}")

    except (ValidationError, HttpError) as e:
        messages.error(request, f"Erro ao criar calendário para {instructor.full_name}: {e}")
        logger.error(f"Erro ao criar calendário para {instructor.full_name}: {e}")

    return redirect('core:google_calendar_instructors')


@role_required(["admin", "staff"])
@require_http_methods(["POST"])
def google_calendar_sync_instructor(request, instructor_id):
    """Sincronizar todos os eventos de um instrutor."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")
    instructor = get_object_or_404(Instructor, id=instructor_id, organization=organization)

    try:
        service = get_google_calendar_service(organization)
        stats = service.sync_all_instructor_events(instructor)

        messages.success(
            request,
            f"Sincronização completa para {instructor.full_name}: "
            f"{stats['success']} eventos exportados, "
            f"{stats['imported']} importados, "
            f"{stats['errors']} erros, "
            f"{stats['skipped']} ignorados."
        )
        logger.info(f"Sincronização manual completa para {instructor.full_name}: {stats}")

    except HttpError as e:
        messages.error(request, f"Erro na sincronização para {instructor.full_name}: {e}")
        logger.error(f"Erro na sincronização para {instructor.full_name}: {e}")

    return redirect('core:google_calendar_instructors')


@role_required(["admin", "staff"])
@require_http_methods(["POST"])
def google_calendar_toggle_instructor_sync(request, instructor_id):
    """Ativar/desativar sincronização para um instrutor."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")
    instructor = get_object_or_404(Instructor, id=instructor_id, organization=organization)

    try:
        config, created = InstructorGoogleCalendar.objects.get_or_create(
            instructor=instructor,
            defaults={'sync_enabled': True}
        )

        if not created:
            config.sync_enabled = not config.sync_enabled
            config.save()

        status = "ativada" if config.sync_enabled else "desativada"
        messages.success(request, f"Sincronização {status} para {instructor.full_name}.")

    except (ValidationError, IntegrityError) as e:
        messages.error(request, f"Erro ao alterar sincronização: {e}")
        logger.error(f"Erro ao alterar sincronização para {instructor.full_name}: {e}")

    return redirect('core:google_calendar_instructors')


@role_required(["admin", "staff"])
def google_calendar_sync_logs(request):
    """Página de logs de sincronização."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")

    # Filtros
    instructor_id = request.GET.get('instructor')
    sync_type = request.GET.get('sync_type')
    status = request.GET.get('status')

    logs = GoogleCalendarSyncLog.objects.filter(organization=organization)

    if instructor_id:
        logs = logs.filter(instructor_id=instructor_id)
    if sync_type:
        logs = logs.filter(sync_type=sync_type)
    if status:
        logs = logs.filter(status=status)

    logs = logs.select_related('instructor', 'event')[:100]  # Limitar a 100 registos

    # Para filtros
    instructors = Instructor.objects.filter(organization=organization, is_active=True)

    context = {
        'logs': logs,
        'instructors': instructors,
        'sync_types': GoogleCalendarSyncLog.SyncType.choices,
        'statuses': GoogleCalendarSyncLog.Status.choices,
        'filters': {
            'instructor': instructor_id,
            'sync_type': sync_type,
            'status': status
        }
    }

    return render(request, 'core/google_calendar/sync_logs.html', context)


@role_required(["admin", "staff"])
def google_calendar_api_sync_event(request, event_id):
    """API endpoint para sincronizar evento específico."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")

    try:
        event = Event.objects.get(id=event_id, organization=organization)

        service = get_google_calendar_service(organization)
        success = service.sync_event_to_google(event)

        if success:
            return JsonResponse({
                'success': True,
                'message': f'Evento "{event.title}" sincronizado com sucesso!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Evento "{event.title}" não foi sincronizado (verificar configurações).'
            })

    except Event.DoesNotExist:
        return JsonResponse({'error': 'Evento não encontrado'}, status=404)
    except (ValidationError, HttpError) as e:
        logger.error(f"Erro na API de sincronização para evento {event_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@role_required(["admin", "staff"])
def google_calendar_settings(request):
    """Página de configurações avançadas do Google Calendar."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")

    try:
        config = GoogleCalendarConfig.objects.get(organization=organization)
    except GoogleCalendarConfig.DoesNotExist:
        messages.error(request, "Configure primeiro o Google Calendar.")
        return redirect('core:google_calendar_setup')

    if request.method == 'POST':
        # Atualizar configurações
        config.auto_sync_events = request.POST.get('auto_sync_events') == 'on'
        config.sync_interval_hours = int(request.POST.get('sync_interval_hours', 1))
        config.save()

        messages.success(request, "Configurações atualizadas com sucesso!")
        return redirect('core:google_calendar_settings')

    context = {
        'config': config,
        'organization': organization
    }

    return render(request, 'core/google_calendar/settings.html', context)


@role_required(["admin", "staff"])
@require_http_methods(["POST"])
def google_calendar_export_backup(request):
    """Exportar ficheiro de backup para o Google Drive."""
    try:
        organization = get_current_organization(request)
    except Organization.DoesNotExist:
        raise Http404("Nenhuma organização configurada.")

    file_path = request.POST.get('file_path', '').strip()
    if not file_path:
        messages.error(request, "Ficheiro de backup não especificado.")
        return redirect('core:google_calendar_setup')

    try:
        service = get_google_calendar_service(organization)
        service.upload_backup_to_drive(file_path)
        messages.success(request, "Backup exportado para Google Drive com sucesso!")
        logger.info(f"Backup {file_path} exportado para Google Drive")
    except (ValidationError, HttpError, OSError) as e:
        messages.error(request, f"Erro ao exportar backup: {e}")
        logger.error(f"Erro ao exportar backup {file_path}: {e}")

    return redirect('core:google_calendar_setup')
