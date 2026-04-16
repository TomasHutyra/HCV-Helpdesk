from django.db import migrations, models


def create_initial_areas(apps, schema_editor):
    Area = apps.get_model('tickets', 'Area')
    Area.objects.create(name='IT', is_unknown=False)
    Area.objects.create(name='Helios', is_unknown=False)
    Area.objects.create(name='Neznámá', is_unknown=True)


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0002_alter_ticket_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='název')),
                ('is_unknown', models.BooleanField(default=False, verbose_name='neznámá oblast')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'oblast',
                'verbose_name_plural': 'oblasti',
                'ordering': ['name'],
            },
        ),
        migrations.RunPython(create_initial_areas, reverse_code=migrations.RunPython.noop),
    ]
