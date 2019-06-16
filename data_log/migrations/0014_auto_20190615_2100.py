# Generated by Django 2.1.7 on 2019-06-16 04:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_log', '0013_auto_20190613_2107'),
    ]

    operations = [
        migrations.AlterField(
            model_name='magicboxcraftrunecraftdrop',
            name='type',
            field=models.IntegerField(choices=[(0, 'Grindstone'), (1, 'Enchant Gem'), (2, 'Immemorial Grindstone'), (3, 'Immemorial Gem'), (4, 'Ancient Grindstone'), (5, 'Ancient Gem')]),
        ),
        migrations.AlterField(
            model_name='riftdungeonrunecraftdrop',
            name='type',
            field=models.IntegerField(choices=[(0, 'Grindstone'), (1, 'Enchant Gem'), (2, 'Immemorial Grindstone'), (3, 'Immemorial Gem'), (4, 'Ancient Grindstone'), (5, 'Ancient Gem')]),
        ),
        migrations.AlterField(
            model_name='riftraidrunecraftdrop',
            name='type',
            field=models.IntegerField(choices=[(0, 'Grindstone'), (1, 'Enchant Gem'), (2, 'Immemorial Grindstone'), (3, 'Immemorial Gem'), (4, 'Ancient Grindstone'), (5, 'Ancient Gem')]),
        ),
    ]
