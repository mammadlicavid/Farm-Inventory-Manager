from django.db import migrations, models


def add_is_favorite_if_missing(apps, schema_editor):
    Supplier = apps.get_model("suppliers", "Supplier")
    table_name = Supplier._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        columns = {
            info.name
            for info in connection.introspection.get_table_description(cursor, table_name)
        }

    if "is_favorite" in columns:
        return

    field = models.BooleanField(default=False, verbose_name="Seçilmiş")
    field.set_attributes_from_name("is_favorite")
    schema_editor.add_field(Supplier, field)


def remove_is_favorite_if_present(apps, schema_editor):
    Supplier = apps.get_model("suppliers", "Supplier")
    table_name = Supplier._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        columns = {
            info.name
            for info in connection.introspection.get_table_description(cursor, table_name)
        }

    if "is_favorite" not in columns:
        return

    field = Supplier._meta.get_field("is_favorite")
    schema_editor.remove_field(Supplier, field)


class Migration(migrations.Migration):

    dependencies = [
        ("suppliers", "0004_alter_supplier_options"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_is_favorite_if_missing, remove_is_favorite_if_present),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="supplier",
                    name="is_favorite",
                    field=models.BooleanField(default=False, editable=False, verbose_name="Seçilmiş"),
                ),
            ],
        ),
    ]
