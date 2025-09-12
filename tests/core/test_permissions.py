import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.test import override_settings

from core.models import Organization, UserProfile


@pytest.fixture
def org():
    return Organization.objects.create(name="Org", domain="example.com")


@pytest.fixture
def admin_user(org):
    user = User.objects.create_user(username="admin_perm", password="pwd")
    UserProfile.objects.create(user=user, organization=org, user_type=UserProfile.UserType.ADMIN)
    return user


@pytest.fixture
def staff_user(org):
    user = User.objects.create_user(username="staff_perm", password="pwd")
    UserProfile.objects.create(user=user, organization=org, user_type=UserProfile.UserType.STAFF)
    return user


@pytest.fixture
def instructor_user(org):
    user = User.objects.create_user(username="inst_perm", password="pwd")
    UserProfile.objects.create(user=user, organization=org, user_type=UserProfile.UserType.INSTRUCTOR)
    return user


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["example.com"])
def test_events_json_permissions(client, org, admin_user, staff_user, instructor_user):
    url = reverse("core:events_json")

    client.force_login(admin_user)
    assert client.get(url, HTTP_HOST="example.com", secure=True).status_code == 200
    client.logout()

    client.force_login(staff_user)
    assert client.get(url, HTTP_HOST="example.com", secure=True).status_code == 200
    client.logout()

    client.force_login(instructor_user)
    assert client.get(url, HTTP_HOST="example.com", secure=True).status_code == 403
