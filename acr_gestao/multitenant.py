# acr_gestao/multitenant.py
from threading import local
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.db.utils import ProgrammingError, OperationalError

try:
    # Import tardio para não rebentar se as migrações ainda não correram
    from core.models import Organization
except Exception:  # pragma: no cover
    Organization = None  # type: ignore

_local = local()

def get_current_org():
    return getattr(_local, "org", None)

class OrganizationMiddleware(MiddlewareMixin):
    """
    Resolve request.organization pelo domínio.
    Se não houver org (ex.: acesso por IP), segue com organization=None (sem rebentar).
    """
    def process_request(self, request):
        host = request.get_host().split(":")[0].lower()
        org = None
        try:
            # Só tenta se:
            # 1) temos o modelo importado, e
            # 2) as tabelas existem.
            if Organization and connection.introspection.table_names():
                try:
                    org = Organization.objects.get(domain=host)
                except Organization.DoesNotExist:
                    org = None
        except (ProgrammingError, OperationalError):
            # BD não pronta → segue sem org
            org = None

        _local.org = org
        request.organization = org
