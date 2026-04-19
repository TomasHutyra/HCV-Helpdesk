from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_managed_areas_m2m'),
        ('tickets', '0003_area'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='resolver_areas',
            field=models.ManyToManyField(
                blank=True,
                help_text='Řešitel vidí nové tikety pouze z těchto oblastí. Ponechte prázdné pro přístup ke všem novým tiketům.',
                related_name='resolving_resolvers',
                to='tickets.area',
                verbose_name='oblasti řešitele',
            ),
        ),
    ]
