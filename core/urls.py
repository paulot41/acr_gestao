from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, web_views

router = DefaultRouter()
router.register(r'people', views.PersonViewSet)
router.register(r'memberships', views.MembershipViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'bookings', views.BookingViewSet)

# URLs da API
api_urlpatterns = [
    path('', include(router.urls)),
]

# URLs da interface web
web_urlpatterns = [
    # Dashboard
    path('', web_views.dashboard, name='dashboard'),

    # Clientes
    path('clientes/', web_views.client_list, name='client_list'),
    path('clientes/<int:pk>/', web_views.client_detail, name='client_detail'),
    path('clientes/novo/', web_views.client_create, name='client_create'),
    path('clientes/<int:pk>/editar/', web_views.client_edit, name='client_edit'),

    # Instrutores
    path('instrutores/', web_views.instructor_list, name='instructor_list'),
    path('instrutores/novo/', web_views.instructor_create, name='instructor_create'),

    # Modalidades
    path('modalidades/', web_views.modality_list, name='modality_list'),
    path('modalidades/nova/', web_views.modality_create, name='modality_create'),

    # Gantt e Eventos
    path('gantt/', web_views.gantt_view, name='gantt_view'),
    path('aulas/', web_views.event_list, name='event_list'),
    path('aulas/nova/', web_views.event_create, name='event_create'),
    path('api/events.json', web_views.events_json, name='events_json'),
]

urlpatterns = [
    path('api/', include(api_urlpatterns)),
] + web_urlpatterns
