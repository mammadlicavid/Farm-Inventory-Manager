from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('animals', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='animal',
            name='batch_id',
            field=models.UUIDField(blank=True, db_index=True, editable=False, null=True),
        ),
    ]
