"""
Serviços de integração com Google Calendar API.
Implementa OAuth2, sincronização de eventos e gestão de calendários.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from ..models import (
    Organization, Event, Instructor, GoogleCalendarConfig,
    InstructorGoogleCalendar, GoogleCalendarSyncLog
)

logger = logging.getLogger(__name__)

# Scopes necessários para Google Calendar
GOOGLE_CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

class GoogleCalendarService:
    """Serviço principal para integração Google Calendar."""

    def __init__(self, organization: Organization):
        self.organization = organization
        self.config = None
        self.service = None
        self._initialize_config()

    def _initialize_config(self):
        """Inicializar configuração Google Calendar para a organização."""
        try:
            self.config = GoogleCalendarConfig.objects.get(organization=self.organization)
        except GoogleCalendarConfig.DoesNotExist:
            self.config = GoogleCalendarConfig.objects.create(organization=self.organization)

    def setup_oauth_flow(self, redirect_uri: str) -> Tuple[str, str]:
        """
        Configura fluxo OAuth2 e retorna URL de autorização.

        Returns:
            Tuple[str, str]: (authorization_url, state)
        """
        if not self.config.client_id or not self.config.client_secret:
            raise ValidationError("Client ID e Client Secret devem estar configurados")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=GOOGLE_CALENDAR_SCOPES
        )
        flow.redirect_uri = redirect_uri

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )

        return authorization_url, state

    def complete_oauth_flow(self, authorization_code: str, redirect_uri: str, state: str):
        """
        Completa fluxo OAuth2 e armazena tokens.

        Args:
            authorization_code: Código de autorização do Google
            redirect_uri: URI de redirecionamento
            state: Estado da sessão OAuth
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=GOOGLE_CALENDAR_SCOPES,
            state=state
        )
        flow.redirect_uri = redirect_uri

        # Trocar código por tokens
        flow.fetch_token(code=authorization_code)

        # Armazenar tokens na configuração
        credentials = flow.credentials
        self.config.access_token = credentials.token
        self.config.refresh_token = credentials.refresh_token
        self.config.token_expiry = credentials.expiry
        self.config.sync_enabled = True
        self.config.save()

        logger.info(f"OAuth2 configurado com sucesso para {self.organization.name}")

    def _get_credentials(self) -> Optional[Credentials]:
        """Obter credenciais válidas, renovando se necessário."""
        if not self.config.access_token:
            return None

        credentials = Credentials(
            token=self.config.access_token,
            refresh_token=self.config.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            scopes=GOOGLE_CALENDAR_SCOPES
        )

        # Renovar token se necessário
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())

                # Atualizar tokens na configuração
                self.config.access_token = credentials.token
                self.config.token_expiry = credentials.expiry
                self.config.save()

                logger.info(f"Token renovado para {self.organization.name}")
            except RefreshError as e:
                logger.error(f"Erro ao renovar token para {self.organization.name}: {e}")
                return None

        return credentials

    def _get_service(self):
        """Obter serviço Google Calendar API."""
        if self.service:
            return self.service

        credentials = self._get_credentials()
        if not credentials:
            raise ValidationError("Credenciais Google Calendar não configuradas ou inválidas")

        self.service = build('calendar', 'v3', credentials=credentials)
        return self.service

    def create_instructor_calendar(self, instructor: Instructor) -> str:
        """
        Criar calendário específico para um instrutor.

        Returns:
            str: ID do calendário criado
        """
        service = self._get_service()

        # Obter ou criar configuração do instrutor
        instructor_config, created = InstructorGoogleCalendar.objects.get_or_create(
            instructor=instructor,
            defaults={
                'calendar_name': f"{instructor.full_name} - Aulas",
                'calendar_color': instructor.modality_set.first().color if instructor.modality_set.exists() else "#0d6efd"
            }
        )

        if instructor_config.google_calendar_id:
            logger.info(f"Calendário já existe para {instructor.full_name}: {instructor_config.google_calendar_id}")
            return instructor_config.google_calendar_id

        try:
            # Criar calendário no Google
            calendar_body = {
                'summary': instructor_config.get_calendar_name(),
                'description': f'Calendário de aulas de {instructor.full_name} - {self.organization.name}',
                'timeZone': 'Europe/Lisbon'
            }

            created_calendar = service.calendars().insert(body=calendar_body).execute()
            calendar_id = created_calendar['id']

            # Atualizar configuração com o ID do calendário
            instructor_config.google_calendar_id = calendar_id
            instructor_config.save()

            # Log da sincronização
            GoogleCalendarSyncLog.objects.create(
                organization=self.organization,
                instructor=instructor,
                sync_type=GoogleCalendarSyncLog.SyncType.CALENDAR_CREATE,
                status=GoogleCalendarSyncLog.Status.SUCCESS,
                google_calendar_id=calendar_id,
                sync_data={'calendar_name': instructor_config.get_calendar_name()}
            )

            logger.info(f"Calendário criado para {instructor.full_name}: {calendar_id}")
            return calendar_id

        except HttpError as e:
            error_msg = f"Erro ao criar calendário para {instructor.full_name}: {e}"
            logger.error(error_msg)

            # Log do erro
            GoogleCalendarSyncLog.objects.create(
                organization=self.organization,
                instructor=instructor,
                sync_type=GoogleCalendarSyncLog.SyncType.CALENDAR_CREATE,
                status=GoogleCalendarSyncLog.Status.ERROR,
                error_message=error_msg
            )

            raise ValidationError(error_msg)

    def sync_event_to_google(self, event: Event) -> bool:
        """
        Sincronizar evento específico para Google Calendar.

        Returns:
            bool: True se sincronizado com sucesso
        """
        if not event.google_calendar_sync_enabled or not event.instructor:
            return False

        service = self._get_service()

        # Obter configuração do instrutor
        try:
            instructor_config = event.instructor.google_calendar
        except InstructorGoogleCalendar.DoesNotExist:
            # Criar calendário se não existe
            self.create_instructor_calendar(event.instructor)
            instructor_config = event.instructor.google_calendar

        if not instructor_config.sync_enabled:
            return False

        # Verificar filtros de entidade
        if event.modality:
            if (event.modality.entity_type == "acr" and not instructor_config.sync_acr_events) or \
               (event.modality.entity_type == "proform" and not instructor_config.sync_proform_events):
                return False

        try:
            # Preparar dados do evento
            event_body = {
                'summary': event.title,
                'description': self._format_event_description(event),
                'start': {
                    'dateTime': event.starts_at.isoformat(),
                    'timeZone': 'Europe/Lisbon',
                },
                'end': {
                    'dateTime': event.ends_at.isoformat(),
                    'timeZone': 'Europe/Lisbon',
                },
                'location': event.resource.name,
                'colorId': self._get_event_color_id(event)
            }

            if event.google_calendar_id:
                # Atualizar evento existente
                updated_event = service.events().update(
                    calendarId=instructor_config.google_calendar_id,
                    eventId=event.google_calendar_id,
                    body=event_body
                ).execute()

                sync_type = GoogleCalendarSyncLog.SyncType.EVENT_UPDATE
                logger.info(f"Evento atualizado no Google Calendar: {event.title}")

            else:
                # Criar novo evento
                created_event = service.events().insert(
                    calendarId=instructor_config.google_calendar_id,
                    body=event_body
                ).execute()

                # Armazenar ID do evento
                event.google_calendar_id = created_event['id']
                event.last_google_sync = timezone.now()
                event.save(update_fields=['google_calendar_id', 'last_google_sync'])

                sync_type = GoogleCalendarSyncLog.SyncType.EVENT_CREATE
                logger.info(f"Evento criado no Google Calendar: {event.title}")

            # Log da sincronização bem-sucedida
            GoogleCalendarSyncLog.objects.create(
                organization=self.organization,
                instructor=event.instructor,
                event=event,
                sync_type=sync_type,
                status=GoogleCalendarSyncLog.Status.SUCCESS,
                google_event_id=event.google_calendar_id,
                google_calendar_id=instructor_config.google_calendar_id,
                sync_data={
                    'event_title': event.title,
                    'starts_at': event.starts_at.isoformat(),
                    'ends_at': event.ends_at.isoformat()
                }
            )

            # Atualizar timestamp de sincronização
            instructor_config.last_sync = timezone.now()
            instructor_config.save(update_fields=['last_sync'])

            return True

        except HttpError as e:
            error_msg = f"Erro ao sincronizar evento {event.title}: {e}"
            logger.error(error_msg)

            # Log do erro
            GoogleCalendarSyncLog.objects.create(
                organization=self.organization,
                instructor=event.instructor,
                event=event,
                sync_type=GoogleCalendarSyncLog.SyncType.EVENT_CREATE if not event.google_calendar_id else GoogleCalendarSyncLog.SyncType.EVENT_UPDATE,
                status=GoogleCalendarSyncLog.Status.ERROR,
                google_calendar_id=instructor_config.google_calendar_id,
                error_message=error_msg
            )

            return False

    def delete_event_from_google(self, event: Event) -> bool:
        """
        Eliminar evento do Google Calendar.

        Returns:
            bool: True se eliminado com sucesso
        """
        if not event.google_calendar_id or not event.instructor:
            return False

        try:
            service = self._get_service()
            instructor_config = event.instructor.google_calendar

            service.events().delete(
                calendarId=instructor_config.google_calendar_id,
                eventId=event.google_calendar_id
            ).execute()

            # Log da eliminação
            GoogleCalendarSyncLog.objects.create(
                organization=self.organization,
                instructor=event.instructor,
                event=event,
                sync_type=GoogleCalendarSyncLog.SyncType.EVENT_DELETE,
                status=GoogleCalendarSyncLog.Status.SUCCESS,
                google_event_id=event.google_calendar_id,
                google_calendar_id=instructor_config.google_calendar_id
            )

            # Limpar ID do evento
            event.google_calendar_id = None
            event.save(update_fields=['google_calendar_id'])

            logger.info(f"Evento eliminado do Google Calendar: {event.title}")
            return True

        except HttpError as e:
            error_msg = f"Erro ao eliminar evento {event.title}: {e}"
            logger.error(error_msg)

            # Log do erro
            GoogleCalendarSyncLog.objects.create(
                organization=self.organization,
                instructor=event.instructor,
                event=event,
                sync_type=GoogleCalendarSyncLog.SyncType.EVENT_DELETE,
                status=GoogleCalendarSyncLog.Status.ERROR,
                error_message=error_msg
            )

            return False

    def sync_all_instructor_events(self, instructor: Instructor) -> Dict[str, int]:
        """
        Sincronizar todos os eventos de um instrutor.

        Returns:
            Dict[str, int]: Estatísticas da sincronização
        """
        stats = {'success': 0, 'errors': 0, 'skipped': 0}

        # Garantir que o calendário existe
        try:
            self.create_instructor_calendar(instructor)
        except (ValidationError, HttpError) as e:
            logger.error(f"Erro ao criar calendário para {instructor.full_name}: {e}")
            return stats

        # Sincronizar eventos futuros (próximos 30 dias)
        future_events = Event.objects.filter(
            instructor=instructor,
            organization=self.organization,
            starts_at__gte=timezone.now(),
            starts_at__lte=timezone.now() + timedelta(days=30),
            google_calendar_sync_enabled=True
        )

        for event in future_events:
            try:
                if self.sync_event_to_google(event):
                    stats['success'] += 1
                else:
                    stats['skipped'] += 1
            except HttpError as e:
                logger.error(f"Erro ao sincronizar evento {event.title}: {e}")
                stats['errors'] += 1

        logger.info(f"Sincronização completa para {instructor.full_name}: {stats}")
        return stats

    def _format_event_description(self, event: Event) -> str:
        """Formatar descrição do evento para Google Calendar."""
        description_parts = []

        if event.modality:
            description_parts.append(f"Modalidade: {event.modality.name}")

        if event.resource:
            description_parts.append(f"Local: {event.resource.name}")

        if event.capacity:
            booked = event.bookings_count
            description_parts.append(f"Ocupação: {booked}/{event.capacity}")

        if event.description:
            description_parts.append(f"\n{event.description}")

        description_parts.append(f"\n--- ACR Gestão ---")
        description_parts.append(f"Sistema: {self.organization.name}")

        return "\n".join(description_parts)

    def _get_event_color_id(self, event: Event) -> str:
        """Obter ID da cor para o evento baseado na modalidade."""
        # Mapeamento de cores hexadecimais para IDs de cor do Google Calendar
        color_mapping = {
            '#0d6efd': '1',  # Azul
            '#198754': '2',  # Verde
            '#ffc107': '5',  # Amarelo
            '#dc3545': '4',  # Vermelho
            '#6f42c1': '3',  # Roxo
            '#fd7e14': '6',  # Laranja
        }

        if event.modality and event.modality.color:
            return color_mapping.get(event.modality.color, '1')

        return '1'  # Azul por defeito


def get_google_calendar_service(organization: Organization) -> GoogleCalendarService:
    """Factory function para obter serviço Google Calendar."""
    return GoogleCalendarService(organization)
