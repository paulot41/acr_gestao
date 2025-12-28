from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .services import get_summary_data


@login_required
def dashboard(request):
    if not getattr(request, "organization", None):
        raise Http404("Organização não encontrada.")
    return render(request, 'reports/dashboard.html')


@login_required
def summary_data(request):
    organization = getattr(request, "organization", None)
    if not organization:
        return JsonResponse({"error": "organization_not_found"}, status=404)
    data = get_summary_data(organization)
    return JsonResponse(data)
