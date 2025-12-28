from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_alter_booking_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="gym_monthly_fee",
            field=models.DecimalField(
                decimal_places=2,
                default=30.0,
                max_digits=10,
                validators=[MinValueValidator(Decimal("0.00"))],
                verbose_name="Mensalidade Ginásio (ACR)",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="wellness_monthly_fee",
            field=models.DecimalField(
                decimal_places=2,
                default=45.0,
                max_digits=10,
                validators=[MinValueValidator(Decimal("0.00"))],
                verbose_name="Mensalidade Pilates (Proform)",
            ),
        ),
        migrations.AddConstraint(
            model_name="event",
            constraint=models.CheckConstraint(
                check=models.Q(("ends_at__gt", models.F("starts_at"))),
                name="event_ends_after_starts",
            ),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["organization", "status"], name="booking_org_status_idx"),
        ),
        migrations.AlterField(
            model_name="instructorcommission",
            name="commission_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=60.0,
                max_digits=5,
                validators=[
                    MinValueValidator(Decimal("0.00")),
                    MaxValueValidator(Decimal("100.00")),
                ],
                verbose_name="Taxa Comissão (%)",
            ),
        ),
        migrations.AlterField(
            model_name="instructorcommission",
            name="entity_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                max_digits=10,
                validators=[MinValueValidator(Decimal("0.00"))],
                verbose_name="Valor Entidade",
            ),
        ),
        migrations.AlterField(
            model_name="instructorcommission",
            name="instructor_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                max_digits=10,
                validators=[MinValueValidator(Decimal("0.00"))],
                verbose_name="Valor Instrutor",
            ),
        ),
        migrations.AlterField(
            model_name="instructorcommission",
            name="total_revenue",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                max_digits=10,
                validators=[MinValueValidator(Decimal("0.00"))],
                verbose_name="Receita Total",
            ),
        ),
    ]
