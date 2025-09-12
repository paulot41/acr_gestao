"""
Middleware personalizado para ACR Gestão.
Funcionalidades multi-tenant e gestão de organizações.
"""

from django.http import Http404
from django.db import IntegrityError, ProgrammingError, OperationalError, connection
from django.core.exceptions import ValidationError
from .models import Organization
import logging

logger = logging.getLogger(__name__)


class OrganizationMiddleware:
    """Middleware melhorado para gestão de multi-tenancy com fallbacks inteligentes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip para URLs administrativas e de autenticação
        skip_paths = ['/admin/', '/login/', '/logout/', '/static/', '/media/']
        if any(request.path.startswith(path) for path in skip_paths):
            response = self.get_response(request)
            return response

        # Determinar organização baseada no domínio
        host = request.get_host().split(':')[0]  # Remove porta se existir

        organization = None
        try:
            if connection.introspection.table_names():
                try:
                    # Tentar encontrar organização por domínio exato
                    organization = Organization.objects.get(domain=host)
                except Organization.DoesNotExist:
                    try:
                        # Fallback: tentar encontrar por domínio similar (desenvolvimento)
                        if 'localhost' in host or '127.0.0.1' in host:
                            organization = Organization.objects.filter(domain__contains='local').first()
                            if not organization:
                                # Criar organização padrão para desenvolvimento
                                organization = Organization.objects.create(
                                    name="ACR Gestão - Desenvolvimento",
                                    domain=host,
                                    org_type="both"
                                )
                                logger.info(f"Organização de desenvolvimento criada: {host}")
                        else:
                            # Em produção, retornar 404 se não encontrar organização
                            raise Http404(f"Organização não encontrada para domínio: {host}")
                    except (IntegrityError, ValidationError) as e:
                        logger.error(f"Erro ao determinar organização: {e}")
                        raise Http404("Erro de configuração do sistema")
        except (ProgrammingError, OperationalError):
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

        # Adicionar headers de segurança
        if organization:
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

    # Fallback: retornar primeira organização disponível
    organization = Organization.objects.first()
    if organization is None:
        raise Organization.DoesNotExist("Nenhuma organização configurada")
    return organization
