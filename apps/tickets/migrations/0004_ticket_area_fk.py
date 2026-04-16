from django.db import migrations, models
import django.db.models.deletion


def migrate_area_to_fk(apps, schema_editor):
    Ticket = apps.get_model('tickets', 'Ticket')
    Area = apps.get_model('tickets', 'Area')

    area_map = {
        'it': Area.objects.get(name='IT'),
        'helios': Area.objects.get(name='Helios'),
        'unknown': Area.objects.get(is_unknown=True),
    }
    for ticket in Ticket.objects.all():
        ticket.area_fk = area_map.get(ticket.area_legacy, area_map['unknown'])
        ticket.save(update_fields=['area_fk'])


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0003_area'),
    ]

    operations = [
        # 1. Přejmenovat staré pole
        migrations.RenameField(
            model_name='ticket',
            old_name='area',
            new_name='area_legacy',
        ),
        # 2. Přidat nové FK pole (nullable)
        migrations.AddField(
            model_name='ticket',
            name='area_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tickets',
                to='tickets.area',
                verbose_name='oblast',
            ),
        ),
        # 3. Datová migrace
        migrations.RunPython(migrate_area_to_fk, reverse_code=migrations.RunPython.noop),
        # 4. Odstranit staré pole
        migrations.RemoveField(
            model_name='ticket',
            name='area_legacy',
        ),
        # 5. Přejmenovat FK pole na area
        migrations.RenameField(
            model_name='ticket',
            old_name='area_fk',
            new_name='area',
        ),
    ]
