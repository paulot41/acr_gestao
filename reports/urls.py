from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('data/summary/', views.summary_data, name='summary_data'),
]
