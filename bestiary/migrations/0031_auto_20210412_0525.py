# Generated by Django 2.2.18 on 2021-04-12 12:25

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bestiary', '0030_remove_skill_skill_effect'),
    ]

    operations = [
        migrations.AlterField(
            model_name='building',
            name='stat_bonus',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(blank=True, null=True), size=None),
        ),
    ]