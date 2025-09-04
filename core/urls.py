from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .admin import admin_site
from . import web_views
from . import auth_views

router = DefaultRouter()
router.register(r'people', views.PersonViewSet)
router.register(r'memberships', views.MembershipViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'bookings', views.BookingViewSet)

urlpatterns = [
    # API REST
    path('api/', include(router.urls)),

    # Admin Unificado (Custom Admin Site)
    path('admin/', admin_site.urls),

    # Sistema de Autenticação Web Personalizado
    path('login/', auth_views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.CustomLogoutView.as_view(), name='logout'),
    path('profile/', auth_views.profile_view, name='profile'),

    # Dashboard Principal (FASE 1)
    path('dashboard/', web_views.dashboard, name='dashboard'),
    path('', web_views.dashboard, name='home'),  # Root agora vai para dashboard

    # Sistema Gantt (CORE FEATURE DA FASE 1)
    path('gantt-system/', web_views.gantt_system, name='gantt_system'),
    path('gantt/', web_views.gantt_view, name='gantt_view'),

    # CRUD Completo de Clientes (FASE 1)
    path('clientes/', web_views.client_list, name='client_list'),
    path('clientes/<int:pk>/', web_views.client_detail, name='client_detail'),
    path('clientes/novo/', web_views.client_create, name='client_create'),
    path('clientes/<int:pk>/editar/', web_views.client_edit, name='client_edit'),

    # CRUD Completo de Instrutores (FASE 1)
    path('instrutores/', web_views.instructor_list, name='instructor_list'),
    path('instrutores/<int:pk>/', web_views.instructor_detail, name='instructor_detail'),
    path('instrutores/novo/', web_views.instructor_create, name='instructor_create'),
    path('instrutores/<int:pk>/editar/', web_views.instructor_edit, name='instructor_edit'),

    # CRUD Completo de Modalidades (FASE 1)
    path('modalidades/', web_views.modality_list, name='modality_list'),
    path('modalidades/nova/', web_views.modality_create, name='modality_create'),
    path('modalidades/<int:pk>/editar/', web_views.modality_edit, name='modality_edit'),

    # CRUD Completo de Aulas/Eventos (FASE 1)
    path('aulas/', web_views.event_list, name='event_list'),
    path('aulas/nova/', web_views.event_create, name='event_create'),
    path('aulas/<int:pk>/editar/', web_views.event_edit, name='event_edit'),

    # API JSON para Sistema Gantt
    path('api/events.json', web_views.events_json, name='events_json'),
]
