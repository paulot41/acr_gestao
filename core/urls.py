from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin
from . import views, web_views, auth_views, dashboard_views, google_calendar_views


class LoginRequiredRedirectView(LoginRequiredMixin, RedirectView):
    pass

app_name = 'core'

urlpatterns = [
    # Dashboard como página inicial
    path('', dashboard_views.admin_dashboard, name='home'),

    # Dashboard adicional (manter para compatibilidade)
    path('dashboard/', dashboard_views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/router/', dashboard_views.dashboard_router, name='dashboard_router'),
    path('dashboard/clients/', dashboard_views.clients_overview, name='admin_clients_overview'),
    path('dashboard/instructors/', dashboard_views.instructors_overview, name='admin_instructors_overview'),

    # Auth
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),

    # Credit History
    path('credit-history/', dashboard_views.credit_history_view, name='credit_history'),

    # Rotas antigas que redirecionam para o Gantt
    path('schedule/', LoginRequiredRedirectView.as_view(pattern_name='core:gantt', permanent=False), name='schedule'),

    # Clientes
    path('clients/', web_views.client_list, name='client_list'),
    path('clients/add/', web_views.client_add, name='client_add'),
    path('modalities/', web_views.modality_list, name='modality_list'),
    path('modalities/add/', web_views.modality_add, name='modality_add'),
    path('clients/<int:pk>/', LoginRequiredRedirectView.as_view(url='/admin/core/person/%(pk)d/change/'), name='client_detail'),
    path('clients/<int:pk>/edit/', LoginRequiredRedirectView.as_view(url='/admin/core/person/%(pk)d/change/'), name='client_edit'),

    # Instrutores
    path('instructors/', web_views.instructor_list, name='instructor_list'),
    path('instructors/add/', web_views.instructor_add, name='instructor_add'),
    path('instructors/<int:pk>/', web_views.instructor_detail, name='instructor_detail'),
    path('instructors/<int:pk>/edit/', web_views.instructor_edit, name='instructor_edit'),

    # Eventos
    path('events/', web_views.event_list, name='event_list'),
    path('events/add/', web_views.event_add, name='event_add'),
    path('events/create/', web_views.event_create, name='event_create'),
    path('events/<int:pk>/edit/', web_views.event_edit, name='event_edit'),
    path('events/<int:pk>/delete/', web_views.event_delete, name='event_delete'),

    # Reservas
    path('bookings/', web_views.booking_list, name='booking_list'),
    path('bookings/add/', web_views.booking_add, name='booking_add'),

    # Gantt
    path('gantt/', views.gantt_view, name='gantt'),
    # Alias para compatibilidade com templates antigos
    path('gantt/', views.gantt_view, name='gantt_view'),
    path('gantt/data/', views.gantt_data, name='gantt_data'),
    path('gantt-system/', web_views.gantt_system, name='gantt_system'),
    path('gantt/events-json/', web_views.events_json, name='events_json'),
    path('gantt/create-event/', views.create_event_from_gantt, name='create_event_from_gantt'),
    path('gantt/update-event/', views.update_event_details, name='update_event_details'),
    path('gantt/event/<int:event_id>/details/', views.get_event_details, name='get_event_details'),

    # Google Calendar
    path('google-calendar/', LoginRequiredRedirectView.as_view(pattern_name='core:google_calendar_setup'), name='google_calendar_home'),
    path('google-calendar/setup/', google_calendar_views.google_calendar_setup, name='google_calendar_setup'),
    path('google-calendar/instructors/', google_calendar_views.google_calendar_instructors, name='google_calendar_instructors'),
    path('google-calendar/instructors/<int:instructor_id>/create/', google_calendar_views.google_calendar_create_instructor_calendar, name='google_calendar_create_instructor_calendar'),
    path('google-calendar/instructors/<int:instructor_id>/sync/', google_calendar_views.google_calendar_sync_instructor, name='google_calendar_sync_instructor'),
    path('google-calendar/instructors/<int:instructor_id>/toggle/', google_calendar_views.google_calendar_toggle_instructor_sync, name='google_calendar_toggle_instructor_sync'),
    path('google-calendar/sync-logs/', google_calendar_views.google_calendar_sync_logs, name='google_calendar_sync_logs'),
    path('google-calendar/settings/', google_calendar_views.google_calendar_settings, name='google_calendar_settings'),
    path('google-calendar/oauth/start/', google_calendar_views.google_calendar_oauth_start, name='google_calendar_oauth_start'),
    path('google-calendar/oauth/callback/', google_calendar_views.google_calendar_oauth_callback, name='google_calendar_oauth_callback'),
    path('google-calendar/save-credentials/', google_calendar_views.google_calendar_save_credentials, name='google_calendar_save_credentials'),
    path('google-calendar/api/event/<int:event_id>/sync/', google_calendar_views.google_calendar_api_sync_event, name='google_calendar_api_sync_event'),
    path('google-calendar/export-backup/', google_calendar_views.google_calendar_export_backup, name='google_calendar_export_backup'),

    # Settings
    path('settings/', web_views.organization_settings, name='settings'),

    # APIs
    path('api/gantt/resources/', views.OptimizedGanttAPI.gantt_resources, name='api_gantt_resources'),
    path('api/gantt/events/', views.OptimizedGanttAPI.gantt_events_fast, name='api_gantt_events'),
    path('api/gantt/create/', views.OptimizedGanttAPI.gantt_create_event, name='api_gantt_create'),
    path('api/form-data/', views.get_form_data, name='api_form_data'),
    path('api/validate-conflict/', views.validate_event_conflict, name='api_validate_conflict'),
    path('api/bookings/<int:booking_id>/cancel/', views.cancel_booking_api, name='api_cancel_booking'),

    # Espaços (Resources)
    path('resources/', web_views.resource_list, name='resource_list'),
    path('resources/add/', web_views.resource_add, name='resource_add'),
    path('resources/<int:pk>/edit/', web_views.resource_edit, name='resource_edit'),
]
