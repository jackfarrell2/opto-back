# Generated by Django 4.2.9 on 2024-01-26 03:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('nba', '0015_userplayer'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userplayer',
            old_name='player',
            new_name='meta_player',
        ),
    ]
