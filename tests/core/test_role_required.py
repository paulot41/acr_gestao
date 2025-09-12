import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.test import override_settings

from core.models import Organization, UserProfile


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["example.com"])
def test_dashboard_admin_role_permissions(client):
    org = Organization.objects.create(name="Org", domain="example.com")

    admin_user = User.objects.create_user(username="admin", password="pwd")
    UserProfile.objects.create(user=admin_user, organization=org, user_type=UserProfile.UserType.ADMIN)

    instructor_user = User.objects.create_user(username="inst", password="pwd")
    UserProfile.objects.create(user=instructor_user, organization=org, user_type=UserProfile.UserType.INSTRUCTOR)

    client.force_login(admin_user)
    resp = client.get(
        reverse("core:admin_dashboard"),
        HTTP_HOST="example.com",
        secure=True,
        follow=True,
    )
    assert resp.status_code == 200

    client.logout()
    client.force_login(instructor_user)
    resp = client.get(
        reverse("core:admin_dashboard"),
        HTTP_HOST="example.com",
        secure=True,
        follow=False,
    )
    assert resp.status_code == 403
