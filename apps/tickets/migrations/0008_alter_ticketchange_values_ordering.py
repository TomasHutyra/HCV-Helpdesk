from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0007_ticketchange'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticketchange',
            name='old_value',
            field=models.TextField(blank=True, verbose_name='původní hodnota'),
        ),
        migrations.AlterField(
            model_name='ticketchange',
            name='new_value',
            field=models.TextField(blank=True, verbose_name='nová hodnota'),
        ),
        migrations.AlterModelOptions(
            name='ticketchange',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'změna tiketu',
                'verbose_name_plural': 'změny tiketu',
            },
        ),
    ]
