import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from core.middleware import OrganizationMiddleware
from core.models import Organization


@override_settings(ALLOWED_HOSTS=["example.com"])
@pytest.mark.django_db
def test_organization_middleware_attaches_org_and_headers():
    org = Organization.objects.create(name="Org", domain="example.com")
    rf = RequestFactory()
    request = rf.get("/", HTTP_HOST="example.com")

    def get_response(req):
        return HttpResponse("OK")

    middleware = OrganizationMiddleware(get_response)
    response = middleware(request)

    assert request.organization == org
    assert request.org_settings["org_name"] == org.name
    assert response["X-Organization-Domain"] == org.domain
    assert response["X-Organization-Type"] == org.org_type
