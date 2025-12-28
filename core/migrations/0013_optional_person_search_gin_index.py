from django.db import migrations


INDEX_NAME = "core_person_search_6ddb47_gin"


def add_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS {name} ON core_person USING GIN (search)".format(
            name=INDEX_NAME
        )
    )


def remove_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "DROP INDEX IF EXISTS {name}".format(name=INDEX_NAME)
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_adjust_unique_constraints"),
    ]

    operations = [
        migrations.RunPython(add_index, remove_index),
    ]
