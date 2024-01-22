# Generated by Django 4.2.9 on 2024-01-22 02:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nba', '0004_remove_player_position_remove_position_slate_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='player',
            name='positions',
        ),
        migrations.DeleteModel(
            name='Position',
        ),
        migrations.AddField(
            model_name='player',
            name='positions',
            field=models.CharField(blank=True, choices=[('F', 'Forward'), ('C', 'Center'), ('G', 'Guard'), ('PG', 'Point Guard'), ('SG', 'Shooting Guard'), ('PF', 'Power Forward'), ('SF', 'Small Forward'), ('UTIL', 'Utility')], max_length=10, null=True),
        ),
    ]