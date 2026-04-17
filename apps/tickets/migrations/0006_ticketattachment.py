import apps.tickets.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0005_alter_area_is_unknown'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=apps.tickets.models.attachment_upload_path, verbose_name='soubor')),
                ('original_name', models.CharField(max_length=255, verbose_name='název souboru')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='nahráno')),
                ('ticket', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attachments',
                    to='tickets.ticket',
                    verbose_name='tiket',
                )),
                ('uploaded_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='attachments',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='nahrál',
                )),
            ],
            options={
                'verbose_name': 'příloha',
                'verbose_name_plural': 'přílohy',
                'ordering': ['created_at'],
            },
        ),
    ]
