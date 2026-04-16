from django.db import migrations, models
from django.conf import settings


def copy_area_fk_to_m2m(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.filter(managed_area__isnull=False):
        user.managed_areas.add(user.managed_area)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_managed_area_fk'),
        ('tickets', '0003_area'),
    ]

    operations = [
        # 1. Přidat nové M2M pole
        migrations.AddField(
            model_name='user',
            name='managed_areas',
            field=models.ManyToManyField(
                blank=True,
                help_text='Správce vidí pouze tikety těchto oblastí. Ponechte prázdné pro přístup ke všem oblastem.',
                related_name='managing_managers',
                to='tickets.area',
                verbose_name='spravované oblasti',
            ),
        ),
        # 2. Datová migrace: přenést stávající FK hodnotu do M2M
        migrations.RunPython(copy_area_fk_to_m2m, reverse_code=migrations.RunPython.noop),
        # 3. Odstranit staré FK pole
        migrations.RemoveField(
            model_name='user',
            name='managed_area',
        ),
    ]
