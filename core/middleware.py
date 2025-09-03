from django.http import Http404
from .models import Organization


class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Assumir primeira organização por agora
            try:
                request.organization = Organization.objects.first()
            except Organization.DoesNotExist:
                request.organization = None
        else:
            request.organization = None

        return self.get_response(request)