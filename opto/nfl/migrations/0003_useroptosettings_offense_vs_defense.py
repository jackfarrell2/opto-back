# Generated by Django 4.2.9 on 2024-08-26 00:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nfl', '0002_player_qb'),
    ]

    operations = [
        migrations.AddField(
            model_name='useroptosettings',
            name='offense_vs_defense',
            field=models.IntegerField(default=0),
        ),
    ]
