# Generated by Django 2.1.7 on 2019-03-05 05:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_log', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dungeonsecretdungeondrop',
            name='monster',
        ),
    ]
