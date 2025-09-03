from django.db import migrations, models
import django.db.models.deletion

def noop_forward(apps, schema_editor):
    # No data to backfill; tables are empty in fresh Postgres.
    pass

def noop_reverse(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_classtemplate_resource_event_booking'),
    ]

    operations = [
        # Organization.settings_json
        migrations.AddField(
            model_name='organization',
            name='settings_json',
            field=models.JSONField(default=dict, blank=True, null=True),
        ),

        # Booking.organization (FK)
        migrations.AddField(
            model_name='booking',
            name='organization',
            field=models.ForeignKey(
                to='core.organization',
                on_delete=django.db.models.deletion.CASCADE,
                null=True,
            ),
        ),

        # Booking.created_at
        migrations.AddField(
            model_name='booking',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),

        # Resource.name
        migrations.AddField(
            model_name='resource',
            name='name',
            field=models.CharField(max_length=120, null=True),
        ),

        # ClassTemplate.title
        migrations.AddField(
            model_name='classtemplate',
            name='title',
            field=models.CharField(max_length=140, null=True),
        ),

        # ClassTemplate.default_duration_minutes
        migrations.AddField(
            model_name='classtemplate',
            name='default_duration_minutes',
            field=models.PositiveIntegerField(default=60, null=True),
        ),

        # Event.starts_at
        migrations.AddField(
            model_name='event',
            name='starts_at',
            field=models.DateTimeField(null=True),
        ),

        # Event.ends_at
        migrations.AddField(
            model_name='event',
            name='ends_at',
            field=models.DateTimeField(null=True),
        ),

        # No-op data step (kept for future edits if needed)
        migrations.RunPython(noop_forward, noop_reverse),

        # Tighten nullability to match models.py now that columns exist
        migrations.AlterField(
            model_name='organization',
            name='settings_json',
            field=models.JSONField(default=dict, blank=True),
        ),
        migrations.AlterField(
            model_name='booking',
            name='organization',
            field=models.ForeignKey(
                to='core.organization',
                on_delete=django.db.models.deletion.CASCADE,
                null=False,
            ),
        ),
        migrations.AlterField(
            model_name='booking',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='name',
            field=models.CharField(max_length=120),
        ),
        migrations.AlterField(
            model_name='classtemplate',
            name='title',
            field=models.CharField(max_length=140),
        ),
        migrations.AlterField(
            model_name='classtemplate',
            name='default_duration_minutes',
            field=models.PositiveIntegerField(default=60),
        ),
        migrations.AlterField(
            model_name='event',
            name='starts_at',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='event',
            name='ends_at',
            field=models.DateTimeField(),
        ),
    ]
