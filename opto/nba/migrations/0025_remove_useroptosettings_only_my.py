# Generated by Django 4.0.4 on 2024-02-13 02:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('nba', '0024_useroptosettings_only_my'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='useroptosettings',
            name='only_my',
        ),
    ]
