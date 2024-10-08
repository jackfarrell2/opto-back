# Generated by Django 4.2.9 on 2024-01-22 03:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nba', '0008_remove_player_positions_delete_position_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='player',
            name='positions',
        ),
        migrations.AddField(
            model_name='player',
            name='isC',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='player',
            name='isF',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='player',
            name='isG',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='player',
            name='isPF',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='player',
            name='isPG',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='player',
            name='isSF',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='player',
            name='isSG',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='player',
            name='isUTIL',
            field=models.BooleanField(default=False),
        ),
    ]
