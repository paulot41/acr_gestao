from threading import local
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.db.utils import ProgrammingError, OperationalError
from core.models import Organization

_local = local()

def get_current_org():
    return getattr(_local, "org", None)

class OrganizationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        host = request.get_host().split(":")[0].lower()
        org = None
        try:
            # Só tenta se as tabelas já existem
            if connection.introspection.table_names():
                try:
                    org = Organization.objects.get(domain=host)
                except Organization.DoesNotExist:
                    org = None
        except (ProgrammingError, OperationalError):
            # BD ainda não migrada ou indisponível
            org = None

        _local.org = org
        request.organization = org
