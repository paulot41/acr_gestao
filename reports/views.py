from django.http import JsonResponse
from django.shortcuts import render

from .services import get_summary_data


def dashboard(request):
    return render(request, 'reports/dashboard.html')


def summary_data(_request):
    data = get_summary_data()
    return JsonResponse(data)
