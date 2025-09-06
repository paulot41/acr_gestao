from django.urls import path, include
from django.views.generic import RedirectView
from . import views, web_views, auth_views, dashboard_views
from .admin import admin_site

app_name = 'core'

urlpatterns = [
    # Redirect root to dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),

    # Dashboard routes - NOVOS
    path('dashboard/', dashboard_views.dashboard_router, name='dashboard_router'),
    path('dashboard/admin/', dashboard_views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/staff/', dashboard_views.dashboard_staff, name='dashboard_staff'),
    path('dashboard/instructor/', dashboard_views.dashboard_instructor, name='dashboard_instructor'),
    path('dashboard/client/', dashboard_views.dashboard_client, name='dashboard_client'),
    path('credit-history/', dashboard_views.credit_history_view, name='credit_history'),
    path('alert/<int:alert_id>/read/', dashboard_views.alert_mark_read, name='alert_mark_read'),
    path('alert/<int:alert_id>/dismiss/', dashboard_views.alert_dismiss, name='alert_dismiss'),

    # Auth routes
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),

    # Web application routes
    path('clients/', web_views.client_list, name='client_list'),
    path('clients/add/', web_views.client_add, name='client_add'),
    path('clients/<int:pk>/', web_views.client_detail, name='client_detail'),
    path('clients/<int:pk>/edit/', web_views.client_edit, name='client_edit'),

    path('instructors/', web_views.instructor_list, name='instructor_list'),
    path('instructors/add/', web_views.instructor_add, name='instructor_add'),
    path('instructors/<int:pk>/', web_views.instructor_detail, name='instructor_detail'),
    path('instructors/<int:pk>/edit/', web_views.instructor_edit, name='instructor_edit'),

    path('modalities/', web_views.modality_list, name='modality_list'),
    path('modalities/add/', web_views.modality_add, name='modality_add'),
    path('modalities/<int:pk>/edit/', web_views.modality_edit, name='modality_edit'),

    # Scheduling/Events
    path('schedule/', web_views.schedule_view, name='schedule'),
    path('events/add/', web_views.event_add, name='event_add'),
    path('events/<int:pk>/edit/', web_views.event_edit, name='event_edit'),
    path('events/<int:pk>/delete/', web_views.event_delete, name='event_delete'),

    # Gantt Chart - DYNAMIC GANTT
    path('gantt/', views.gantt_view, name='gantt'),
    path('gantt/data/', views.gantt_data, name='gantt_data'),
    path('gantt/create-event/', views.create_event_from_gantt, name='create_event_from_gantt'),
    path('gantt/update-event/', views.update_event_details, name='update_event_details'),
    path('gantt/event/<int:event_id>/details/', views.get_event_details, name='get_event_details'),

    # APIs Otimizadas
    path('api/gantt/resources/', views.OptimizedGanttAPI.gantt_resources, name='api_gantt_resources'),
    path('api/gantt/events/', views.OptimizedGanttAPI.gantt_events_fast, name='api_gantt_events'),
    path('api/gantt/create/', views.OptimizedGanttAPI.gantt_create_event, name='api_gantt_create'),
    path('api/form-data/', views.get_form_data, name='api_form_data'),
    path('api/validate-conflict/', views.validate_event_conflict, name='api_validate_conflict'),

    # Booking management with credits
    path('api/events/<int:event_id>/book/', views.book_event, name='book_event'),
    path('api/bookings/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),

    # Settings
    path('settings/', web_views.organization_settings, name='settings'),

    # Custom admin interface
    path('admin/', admin_site.urls),
]
