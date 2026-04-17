import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0006_ticketattachment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(max_length=30, verbose_name='pole')),
                ('old_value', models.CharField(blank=True, max_length=300, verbose_name='původní hodnota')),
                ('new_value', models.CharField(blank=True, max_length=300, verbose_name='nová hodnota')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='čas')),
                ('ticket', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='history',
                    to='tickets.ticket',
                    verbose_name='tiket',
                )),
                ('user', models.ForeignKey(
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ticket_changes',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='uživatel',
                )),
            ],
            options={
                'verbose_name': 'změna tiketu',
                'verbose_name_plural': 'změny tiketu',
                'ordering': ['created_at'],
            },
        ),
    ]
