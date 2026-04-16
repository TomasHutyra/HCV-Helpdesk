from django.db import migrations, models
import django.db.models.deletion


def migrate_managed_area_to_fk(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Area = apps.get_model('tickets', 'Area')

    area_map = {
        'it': Area.objects.filter(name='IT').first(),
        'helios': Area.objects.filter(name='Helios').first(),
    }
    for user in User.objects.exclude(managed_area_legacy=''):
        area = area_map.get(user.managed_area_legacy)
        if area:
            user.managed_area_fk = area
            user.save(update_fields=['managed_area_fk'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_managed_area_user_managed_companies'),
        ('tickets', '0003_area'),
    ]

    operations = [
        # 1. Přejmenovat staré pole
        migrations.RenameField(
            model_name='user',
            old_name='managed_area',
            new_name='managed_area_legacy',
        ),
        # 2. Přidat nové FK pole
        migrations.AddField(
            model_name='user',
            name='managed_area_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='managing_managers',
                to='tickets.area',
                verbose_name='oblast správce',
            ),
        ),
        # 3. Datová migrace
        migrations.RunPython(migrate_managed_area_to_fk, reverse_code=migrations.RunPython.noop),
        # 4. Odstranit staré pole
        migrations.RemoveField(
            model_name='user',
            name='managed_area_legacy',
        ),
        # 5. Přejmenovat FK pole
        migrations.RenameField(
            model_name='user',
            old_name='managed_area_fk',
            new_name='managed_area',
        ),
    ]
