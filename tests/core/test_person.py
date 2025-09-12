import pytest
from unittest.mock import MagicMock, patch
from core.models import Organization, Person


@pytest.mark.django_db
def test_get_monthly_fee():
    org = Organization.objects.create(name="Org", domain="org.local", gym_monthly_fee=10, wellness_monthly_fee=20)
    with patch("core.models.SearchVector", return_value="dummy"):
        person_acr = Person.objects.create(
            organization=org,
            first_name="A",
            nif="111",
            email="a@example.com",
            entity_affiliation=Person.EntityAffiliation.ACR_ONLY,
        )
        person_proform = Person.objects.create(
            organization=org,
            first_name="B",
            nif="222",
            email="b@example.com",
            entity_affiliation=Person.EntityAffiliation.PROFORM_ONLY,
        )
        person_both = Person.objects.create(
            organization=org,
            first_name="C",
            nif="333",
            email="c@example.com",
            entity_affiliation=Person.EntityAffiliation.BOTH,
        )

    assert person_acr.get_monthly_fee() == 10
    assert person_proform.get_monthly_fee() == 20
    assert person_both.get_monthly_fee() == 30


@pytest.mark.django_db
def test_person_save_updates_search_vector():
    org = Organization.objects.create(name="Org", domain="org.local")
    person = Person(organization=org, first_name="John", last_name="Doe", email="john@example.com")

    mock_qs = MagicMock()
    with patch("core.models.SearchVector") as mock_sv, patch.object(Person.objects, "filter", return_value=mock_qs) as mock_filter:
        person.save()
        mock_sv.assert_called_once_with("first_name", "last_name", "email", "nif", config="portuguese")
        mock_filter.assert_called_once_with(pk=person.pk)
        mock_qs.update.assert_called_once_with(search=mock_sv.return_value)
