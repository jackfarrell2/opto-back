# Generated by Django 4.2.9 on 2024-08-22 01:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('projection', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('opponent', models.CharField(max_length=5, null=True)),
                ('position', models.CharField(max_length=5)),
                ('RB', models.BooleanField(default=False)),
                ('WR', models.BooleanField(default=False)),
                ('TE', models.BooleanField(default=False)),
                ('FLEX', models.BooleanField(default=False)),
                ('DST', models.BooleanField(default=False)),
                ('dk_id', models.IntegerField()),
                ('salary', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Slate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('game_count', models.IntegerField()),
                ('sport', models.CharField(choices=[('NBA', 'NBA'), ('MLB', 'MLB'), ('NFL', 'NFL'), ('NHL', 'NHL')], max_length=4)),
            ],
        ),
        migrations.CreateModel(
            name='UserPlayer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lock', models.BooleanField(default=False)),
                ('remove', models.BooleanField(default=False)),
                ('ownership', models.DecimalField(decimal_places=2, max_digits=5)),
                ('exposure', models.DecimalField(decimal_places=2, default=100, max_digits=5)),
                ('projection', models.DecimalField(decimal_places=2, max_digits=5)),
                ('meta_player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nfl.player')),
                ('slate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nfl.slate')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_nfl_players', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Player',
            },
        ),
        migrations.CreateModel(
            name='UserOptoSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_salary', models.IntegerField(default=50000)),
                ('min_salary', models.IntegerField(default=49000)),
                ('max_players_per_team', models.IntegerField(default=5)),
                ('uniques', models.IntegerField(default=3)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_nfl_opto_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Opto Setting',
            },
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('abbrev', models.CharField(max_length=5)),
                ('opponent', models.CharField(max_length=5, null=True)),
                ('slate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nfl.slate')),
            ],
        ),
        migrations.AddField(
            model_name='player',
            name='slate',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nfl.slate'),
        ),
        migrations.AddField(
            model_name='player',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teams_players', to='nfl.team'),
        ),
        migrations.CreateModel(
            name='Optimization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lineups', models.JSONField()),
                ('exposures', models.JSONField()),
                ('slate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nfl.slate')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_nfl_opto', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DateTimeField()),
                ('away_team', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='away_game', to='nfl.team')),
                ('home_team', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='home_game', to='nfl.team')),
                ('slate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nfl.slate')),
            ],
        ),
    ]
