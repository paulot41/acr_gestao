from datetime import datetime, timedelta
from unittest import mock

import pytest
from django.utils import timezone

from core.models import (
    Event,
    Instructor,
    Organization,
    Resource,
    GoogleCalendarConfig,
    InstructorGoogleCalendar,
)
from core.services.google_calendar import GoogleCalendarService


@pytest.mark.django_db
def test_setup_oauth_flow(monkeypatch):
    org = Organization.objects.create(name="Org", domain="org.test")
    GoogleCalendarConfig.objects.create(
        organization=org, client_id="cid", client_secret="secret"
    )

    class DummyFlow:
        def __init__(self, *args, **kwargs):
            self.redirect_uri = None

        def authorization_url(self, **kwargs):
            return "http://auth", "state123"

    monkeypatch.setattr(
        "google_auth_oauthlib.flow.Flow.from_client_config",
        lambda config, scopes: DummyFlow(),
    )

    service = GoogleCalendarService(org)
    url, state = service.setup_oauth_flow("http://redirect")

    assert url == "http://auth"
    assert state == "state123"


@pytest.mark.django_db
def test_complete_oauth_flow_stores_tokens(monkeypatch):
    org = Organization.objects.create(name="Org2", domain="org2.test")
    config = GoogleCalendarConfig.objects.create(
        organization=org, client_id="cid", client_secret="secret"
    )

    class DummyCreds:
        token = "tok"
        refresh_token = "ref"
        expiry = datetime.now() + timedelta(hours=1)

    class DummyFlow:
        def __init__(self, *args, **kwargs):
            self.redirect_uri = None
            self.credentials = DummyCreds()

        def fetch_token(self, code):
            return None

    monkeypatch.setattr(
        "google_auth_oauthlib.flow.Flow.from_client_config",
        lambda config, scopes, state=None: DummyFlow(),
    )

    service = GoogleCalendarService(org)
    service.complete_oauth_flow("code", "http://redirect", "state")

    config.refresh_from_db()
    assert config.access_token == "tok"
    assert config.refresh_token == "ref"


@pytest.mark.django_db
def test_sync_events_from_google_updates_event(monkeypatch):
    org = Organization.objects.create(name="Org3", domain="org3.test")
    GoogleCalendarConfig.objects.create(
        organization=org, client_id="cid", client_secret="secret"
    )
    instructor = Instructor.objects.create(organization=org, first_name="Inst")
    resource = Resource.objects.create(organization=org, name="Room")
    InstructorGoogleCalendar.objects.create(instructor=instructor, google_calendar_id="cal1")

    start = timezone.now()
    with mock.patch("core.models.Event.full_clean", lambda self: None):
        event = Event.objects.create(
            organization=org,
            resource=resource,
            instructor=instructor,
            title="Old",
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            capacity=5,
        )
    event.google_calendar_id = "abc"
    event.save(update_fields=["google_calendar_id"])

    class DummyEvents:
        def list(self, **kwargs):
            class Exec:
                def execute(self):
                    return {
                        "items": [
                            {
                                "id": "abc",
                                "summary": "New",
                                "start": {"dateTime": "2025-01-01T10:00:00Z"},
                                "end": {"dateTime": "2025-01-01T11:00:00Z"},
                            }
                        ]
                    }

            return Exec()

    class DummyService:
        def events(self):
            return DummyEvents()

    service = GoogleCalendarService(org)
    monkeypatch.setattr(service, "_get_service", lambda: DummyService())

    stats = service.sync_events_from_google(instructor)
    event.refresh_from_db()

    assert stats["imported"] == 1
    assert event.title == "New"
    assert event.starts_at.hour == 10


@pytest.mark.django_db
def test_upload_backup_to_drive(monkeypatch, tmp_path):
    org = Organization.objects.create(name="Org4", domain="org4.test")
    GoogleCalendarConfig.objects.create(
        organization=org,
        client_id="cid",
        client_secret="secret",
        access_token="tok",
    )

    service = GoogleCalendarService(org)

    dummy_drive = mock.MagicMock()
    dummy_drive.files.return_value.create.return_value.execute.return_value = {
        "id": "file123"
    }

    monkeypatch.setattr("core.services.google_calendar.build", lambda *args, **kwargs: dummy_drive)

    file_path = tmp_path / "backup.txt"
    file_path.write_text("data")

    file_id = service.upload_backup_to_drive(str(file_path))
    assert file_id == "file123"
    assert dummy_drive.files.return_value.create.called

