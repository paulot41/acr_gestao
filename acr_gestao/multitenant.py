from threading import local
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.db.utils import ProgrammingError, OperationalError

try:
    from core.models import Organization
except Exception:
    Organization = None

_local = local()

class OrganizationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        host = request.get_host().split(":")[0].lower()
        org = None
        try:
            if Organization and connection.introspection.table_names():
                org = Organization.objects.filter(domain__iexact=host).first()
        except (ProgrammingError, OperationalError):
            pass
        _local.org = org
        request.organization = org
