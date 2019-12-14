# Generated by Django 2.1.11 on 2019-11-14 19:59

from django.db import migrations


def fill_substat_arrays(apps, schema_editor):
    RuneInstance = apps.get_model('herders', 'RuneInstance')

    runes = RuneInstance.objects.filter(quality__gt=0, substats_grind_value__len=0)

    for r in runes:
        r.substats_enchanted = []
        r.substats_grind_value = []

        for x in range(len(r.substats)):
            if getattr(r, f'substat_{x+1}'):
                r.substats_enchanted.append(getattr(r, f'substat_{x+1}_craft') == 1)
                r.substats_grind_value.append(0)

    RuneInstance.objects.bulk_update(
        runes,
        ['substats_enchanted', 'substats_grind_value'],
        batch_size=5000
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('herders', '0008_auto_20191114_1145'),
        ('bestiary', '0017_gameitem_slug'),
    ]

    operations = [
        migrations.RunPython(fill_substat_arrays, noop)
    ]
