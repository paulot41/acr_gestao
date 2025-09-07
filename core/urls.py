from django.urls import path
from django.views.generic import RedirectView
from django.http import HttpResponse
from . import views, web_views, auth_views, dashboard_views, google_calendar_views
from .admin import admin_site

app_name = 'core'

urlpatterns = [
    # Home/Dashboard => Gantt (corrigir namespace)
    path('', RedirectView.as_view(pattern_name='core:gantt', permanent=False), name='home'),
    path('dashboard/', dashboard_views.dashboard_router, name='dashboard'),

    # Auth
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),

    # Credit History - adicionar URL em falta
    path('credit-history/', dashboard_views.credit_history_view, name='credit_history'),

    # Rotas antigas que agora redirecionam para o Gantt (corrigir namespace)
    path('schedule/', RedirectView.as_view(pattern_name='core:gantt', permanent=False), name='schedule'),
    path('instructors/', RedirectView.as_view(pattern_name='core:gantt', permanent=False), name='instructors'),

    # Clientes (redirecionar para admin)
    path('clients/', RedirectView.as_view(url='/admin/core/person/'), name='client_list'),
    path('modalities/', RedirectView.as_view(url='/admin/core/modality/'), name='modality_list'),
    path('clients/<int:pk>/', RedirectView.as_view(url='/admin/core/person/%(pk)d/change/'), name='client_detail'),
    path('clients/<int:pk>/edit/', RedirectView.as_view(url='/admin/core/person/%(pk)d/change/'), name='client_edit'),
    path('gantt/', views.gantt_view, name='gantt'),
    path('gantt/data/', views.gantt_data, name='gantt_data'),
    path('gantt-system/', web_views.gantt_system, name='gantt_system'),
    path('gantt/create-event/', views.create_event_from_gantt, name='create_event_from_gantt'),
    path('gantt/update-event/', views.update_event_details, name='update_event_details'),
    path('gantt/event/<int:event_id>/details/', views.get_event_details, name='get_event_details'),

    # Google Calendar (FASE 2)
    path('google-calendar/setup/', google_calendar_views.google_calendar_setup, name='google_calendar_setup'),
    path('google-calendar/instructors/', google_calendar_views.google_calendar_instructors, name='google_calendar_instructors'),
    path('google-calendar/sync-logs/', google_calendar_views.google_calendar_sync_logs, name='google_calendar_sync_logs'),
    path('google-calendar/settings/', google_calendar_views.google_calendar_settings, name='google_calendar_settings'),
    path('google-calendar/oauth/start/', google_calendar_views.google_calendar_oauth_start, name='google_calendar_oauth_start'),
    path('google-calendar/oauth/callback/', google_calendar_views.google_calendar_oauth_callback, name='google_calendar_oauth_callback'),

    # APIs
    path('api/gantt/resources/', views.OptimizedGanttAPI.gantt_resources, name='api_gantt_resources'),
    path('api/gantt/events/', views.OptimizedGanttAPI.gantt_events_fast, name='api_gantt_events'),
    path('api/gantt/create/', views.OptimizedGanttAPI.gantt_create_event, name='api_gantt_create'),
    path('api/form-data/', views.get_form_data, name='api_form_data'),
    path('api/validate-conflict/', views.validate_event_conflict, name='api_validate_conflict'),

    # Booking APIs - adicionar URLs para cancelamento de reservas
    path('api/bookings/<int:booking_id>/cancel/', views.cancel_booking_api, name='api_cancel_booking'),

    # Admin
    path('admin/', admin_site.urls),
]
