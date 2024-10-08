# Generated by Django 4.2.9 on 2024-01-22 02:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nba', '0003_player_positions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='player',
            name='position',
        ),
        migrations.RemoveField(
            model_name='position',
            name='slate',
        ),
        migrations.AlterField(
            model_name='position',
            name='position',
            field=models.CharField(choices=[('PG', 'PG'), ('SG', 'SG'), ('SF', 'SF'), ('PF', 'PF'), ('C', 'C'), ('G', 'G'), ('F', 'F'), ('UTIL', 'UTIL')], max_length=5),
        ),
    ]
