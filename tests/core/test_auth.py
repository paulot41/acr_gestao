import pytest
from django.urls import reverse
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_login_valid(client):
    User.objects.create_user(username="john", password="secret")
    url = reverse("core:login")
    response = client.post(url, {"username": "john", "password": "secret"}, secure=True, HTTP_HOST="localhost")
    assert response.status_code == 302
    assert response.url == reverse("core:home")


@pytest.mark.django_db
def test_login_invalid(client):
    User.objects.create_user(username="john", password="secret")
    url = reverse("core:login")
    response = client.post(url, {"username": "john", "password": "wrong"}, secure=True, HTTP_HOST="localhost")
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_login_required_redirect(client):
    url = reverse("core:gantt")
    response = client.get(url, secure=True, HTTP_HOST="localhost")
    assert response.status_code == 302
    assert reverse("core:login") in response.url


@pytest.mark.django_db
def test_role_required_forbidden(client):
    user = User.objects.create_user(username="john", password="secret")
    client.login(username="john", password="secret")
    url = reverse("core:admin_dashboard")
    response = client.get(url, secure=True, HTTP_HOST="localhost")
    assert response.status_code == 403
