from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_person_consent_rgpd"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="person",
            name="unique_person_org_email",
        ),
        migrations.RemoveConstraint(
            model_name="person",
            name="unique_person_org_nif",
        ),
        migrations.AddConstraint(
            model_name="person",
            constraint=models.UniqueConstraint(
                fields=["organization", "email"],
                name="unique_person_org_email",
                condition=~models.Q(email=""),
            ),
        ),
        migrations.AddConstraint(
            model_name="person",
            constraint=models.UniqueConstraint(
                fields=["organization", "nif"],
                name="unique_person_org_nif",
                condition=~models.Q(nif=""),
            ),
        ),
        migrations.AlterUniqueTogether(
            name="instructor",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="instructor",
            constraint=models.UniqueConstraint(
                fields=["organization", "email"],
                name="unique_instructor_org_email",
                condition=~models.Q(email=""),
            ),
        ),
    ]
