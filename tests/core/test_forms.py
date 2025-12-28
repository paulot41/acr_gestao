import pytest

from core.forms import PersonForm, InstructorForm
from core.models import Organization, Person, Instructor


@pytest.mark.django_db
def test_person_form_email_unique_scoped_by_org():
    org1 = Organization.objects.create(name="Org1", domain="org1.test")
    org2 = Organization.objects.create(name="Org2", domain="org2.test")
    Person.objects.create(
        organization=org1,
        first_name="Ana",
        email="dup@example.com",
        nif="123456789",
    )

    data = {
        "first_name": "Bea",
        "last_name": "",
        "email": "dup@example.com",
        "phone": "",
        "nif": "",
        "date_of_birth": "",
        "address": "",
        "emergency_contact": "",
        "entity_affiliation": "acr_only",
        "status": "active",
        "notes": "",
    }

    form_other_org = PersonForm(data=data, organization=org2)
    assert form_other_org.is_valid()

    form_same_org = PersonForm(data=data, organization=org1)
    assert not form_same_org.is_valid()
    assert "email" in form_same_org.errors


@pytest.mark.django_db
def test_instructor_form_email_unique_scoped_by_org():
    org1 = Organization.objects.create(name="Org1", domain="org1b.test")
    org2 = Organization.objects.create(name="Org2", domain="org2b.test")
    Instructor.objects.create(
        organization=org1,
        first_name="Inst",
        email="inst@example.com",
    )

    data = {
        "first_name": "Maria",
        "last_name": "",
        "email": "inst@example.com",
        "phone": "",
        "specialties": "",
        "entity_affiliation": "acr_only",
        "acr_commission_rate": "60",
        "proform_commission_rate": "70",
        "is_active": "on",
    }

    form_other_org = InstructorForm(data=data, organization=org2)
    assert form_other_org.is_valid()

    form_same_org = InstructorForm(data=data, organization=org1)
    assert not form_same_org.is_valid()
    assert "email" in form_same_org.errors
