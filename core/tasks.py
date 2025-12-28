from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

from .models import Organization, Instructor, Event
from .services.google_calendar import get_google_calendar_service


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def sync_instructor_events_task(self, organization_id: int, instructor_id: int) -> dict:
    try:
        organization = Organization.objects.get(id=organization_id)
        instructor = Instructor.objects.get(id=instructor_id, organization=organization)
    except ObjectDoesNotExist as exc:
        return {"success": 0, "imported": 0, "errors": 1, "skipped": 0, "error": str(exc)}

    service = get_google_calendar_service(organization)
    return service.sync_all_instructor_events(instructor)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def sync_event_task(self, organization_id: int, event_id: int) -> dict:
    try:
        organization = Organization.objects.get(id=organization_id)
        event = Event.objects.get(id=event_id, organization=organization)
    except ObjectDoesNotExist as exc:
        return {"success": False, "error": str(exc)}

    service = get_google_calendar_service(organization)
    result = service.sync_event_to_google(event)
    return {"success": bool(result)}
