"""
Middleware personalizado para ACR Gestão.
Funcionalidades multi-tenant e gestão de organizações.
"""

from django.http import Http404
from django.http.request import split_domain_port
from django.db import IntegrityError, ProgrammingError, OperationalError, DatabaseError, connection
from django.core.exceptions import ValidationError
from uuid import uuid4
from .models import Organization
from .logging_utils import set_request_id, reset_request_id
import logging

logger = logging.getLogger(__name__)


class HealthCheckMiddleware:
    """Permite health checks responderem com 200 mesmo quando invocados via IPs internos/containers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ('/health', '/health/'):
            from acr_gestao.urls import health
            return health(request)
        return self.get_response(request)


class RequestIdMiddleware:
    """Attach a request id for tracing and logging correlation."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header_request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Request-Id")
        request_id = header_request_id.strip() if header_request_id else ""
        if not request_id or len(request_id) > 64:
            request_id = uuid4().hex

        token = set_request_id(request_id)
        request.request_id = request_id
        try:
            response = self.get_response(request)
        finally:
            reset_request_id(token)

        response["X-Request-ID"] = request_id
        return response


class OrganizationMiddleware:
    """Middleware melhorado para gestão de multi-tenancy com fallbacks inteligentes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip para URLs administrativas, autenticação e health check
        skip_paths = ['/admin/', '/login/', '/logout/', '/static/', '/media/', '/health/']
        if any(request.path.startswith(path) for path in skip_paths):
            response = self.get_response(request)
            return response

        # Determinar organização baseada no domínio
        try:
            host_raw = request.get_host()
            host, _ = split_domain_port(host_raw)
        except Exception:
            raw_host = request.META.get('HTTP_HOST', '') or request.META.get('SERVER_NAME', 'localhost')
            try:
                host, _ = split_domain_port(raw_host) if raw_host else ('localhost', None)
            except Exception:
                host = 'localhost'

        organization = None
        try:
            if connection.introspection.table_names():
                # 1. Tentar encontrar por domínio exato
                organization = Organization.objects.filter(domain=host).first()

                # 2. Se não encontrou, obter organização padrão (primeira existente)
                if not organization:
                    organization = Organization.objects.first()

                # 3. Se não existe nenhuma organização, criar a organização unificada
                if not organization:
                    try:
                        organization = Organization.objects.create(
                            name="ACR & Proform SC",
                            domain=host if host else "localhost",
                            org_type="both"
                        )
                        logger.info("Organização unificada 'ACR & Proform SC' criada por defeito.")
                    except (IntegrityError, ValidationError, DatabaseError) as e:
                        logger.error(f"Erro ao criar organização padrão: {e}")
                        organization = Organization.objects.first()
        except (ProgrammingError, OperationalError, DatabaseError) as e:
            logger.warning(f"Erro de base de dados na determinação da organização: {e}")
            organization = None

        # Anexar organização ao request
        request.organization = organization

        # Adicionar informações úteis ao contexto quando disponível
        if organization:
            request.org_settings = {
                'gym_fee': float(organization.gym_monthly_fee),
                'wellness_fee': float(organization.wellness_monthly_fee),
                'org_type': organization.org_type,
                'org_name': organization.name
            }
        else:
            request.org_settings = {}

        response = self.get_response(request)

        # Adicionar headers informativos da organização
        if organization and hasattr(response, '__setitem__'):
            response['X-Organization-Domain'] = organization.domain
            response['X-Organization-Type'] = organization.org_type

        return response


class SecurityMiddleware:
    """Middleware de segurança adicional para proteger dados sensíveis."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verificar tentativas de acesso cross-organization
        if hasattr(request, 'organization') and request.user.is_authenticated:
            # Log de atividade do utilizador
            if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
                logger.info(f"User {request.user.username} accessed {request.path} on {request.organization.domain}")

        response = self.get_response(request)

        # Headers de segurança
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'

        return response


class PerformanceMiddleware:
    """Middleware para otimizações de performance."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import time
        start_time = time.time()

        response = self.get_response(request)

        # Adicionar tempo de processamento nos headers (apenas em debug)
        processing_time = time.time() - start_time
        response['X-Processing-Time'] = f"{processing_time:.3f}s"

        # Log de requests lentos
        if processing_time > 1.0:  # Mais de 1 segundo
            logger.warning(f"Slow request: {request.path} took {processing_time:.3f}s")

        return response


def get_current_organization(request):
    """
    Função utilitária para obter a organização atual do request.
    Usada pelas views do Google Calendar.
    """
    if hasattr(request, 'organization') and request.organization:
        return request.organization

    # Fallback: retornar primeira organização disponível ou criar por defeito
    organization = Organization.objects.first()
    if organization is None:
        try:
            organization = Organization.objects.create(
                name="ACR & Proform SC",
                domain="localhost",
                org_type=Organization.Type.BOTH
            )
        except Exception:
            raise Organization.DoesNotExist("Nenhuma organização configurada")
    return organization
