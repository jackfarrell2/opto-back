# Generated by Django 4.0.4 on 2024-02-08 22:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nba', '0021_alter_userplayer_exposure_alter_userplayer_ownership_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userplayer',
            name='exposure',
            field=models.DecimalField(decimal_places=2, default=100, max_digits=5),
        ),
    ]