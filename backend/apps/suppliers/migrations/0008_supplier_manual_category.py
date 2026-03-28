from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0007_merge_optional_and_remove_favorite'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplier',
            name='manual_category',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Kateqoriya (Digər)'),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='category',
            field=models.CharField(choices=[('Toxum', 'Toxum'), ('Gübrə', 'Gübrə'), ('Pestisid', 'Pestisid'), ('Baytarlıq', 'Baytarlıq'), ('Yem', 'Yem'), ('Alətlər', 'Alətlər'), ('Kənd Texnikası', 'Kənd Texnikası'), ('Suvarma', 'Suvarma'), ('Heyvan', 'Heyvan'), ('Digər', 'Digər')], default='Digər', max_length=50, verbose_name='Kateqoriya'),
        ),
    ]
