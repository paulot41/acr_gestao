from django.utils.deprecation import MiddlewareMixin
from threading import local
from core.models import Organization

_local = local()

def get_current_org():
    return getattr(_local, "org", None)

class OrganizationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        host = request.get_host().split(":")[0].lower()
        try:
            org = Organization.objects.get(domain=host)
        except Organization.DoesNotExist:
            org = None
        _local.org = org
        request.organization = org
