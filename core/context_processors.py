"""Context processors para o módulo core."""


def organization_context(request):
    """
    Injeta a organização atual e suas configurações financeiras/gerais
    diretamente no contexto dos templates.
    """
    org = getattr(request, 'organization', None)
    settings = getattr(request, 'org_settings', {})
    return {
        'organization': org,
        'org_settings': settings,
    }
