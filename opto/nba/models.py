from django.db import models
from pytz import timezone
from users.models import CustomUser


class Slate(models.Model):
    OPTION_CHOICES = [
        ('NBA', 'NBA'),
        ('MLB', 'MLB'),
        ('NFL', 'NFL'),
        ('NHL', 'NHL'),
    ]
    date = models.DateTimeField()
    game_count = models.IntegerField()
    sport = models.CharField(max_length=4, choices=OPTION_CHOICES)

    def __str__(self):
        est_version = self.date.astimezone(timezone("America/New_York"))
        time = est_version.strftime("%a %m/%d/%Y, %I:%M%p")
        return f"{time} - {self.game_count} games"


class Team(models.Model):
    abbrev = models.CharField(max_length=5)
    slate = models.ForeignKey(Slate, on_delete=models.CASCADE)
    opponent = models.CharField(max_length=5, null=True)

    def __str__(self):
        return f"{self.abbrev}"


class Player(models.Model):
    name = models.CharField(max_length=50)
    projection = models.DecimalField(max_digits=5,
                                     decimal_places=2,
                                     default=0)
    team = models.ForeignKey(Team,
                             on_delete=models.CASCADE,
                             related_name='teams_players')
    opponent = models.CharField(max_length=5, null=True)
    position = models.CharField(max_length=5)
    F = models.BooleanField(default=False)
    C = models.BooleanField(default=False)
    G = models.BooleanField(default=False)
    SG = models.BooleanField(default=False)
    PG = models.BooleanField(default=False)
    SF = models.BooleanField(default=False)
    PF = models.BooleanField(default=False)
    UTIL = models.BooleanField(default=False)
    dk_id = models.IntegerField()
    salary = models.IntegerField()
    slate = models.ForeignKey(Slate, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}"


class Game(models.Model):
    time = models.DateTimeField()
    home_team = models.OneToOneField(Team,
                                     on_delete=models.CASCADE,
                                     related_name='home_game')
    away_team = models.OneToOneField(Team,
                                     on_delete=models.CASCADE,
                                     related_name='away_game')
    slate = models.ForeignKey(Slate, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.away_team} @ {self.home_team}"


class UserPlayer(models.Model):

    class Meta:
        verbose_name = 'User Player'

    meta_player = models.ForeignKey(Player, on_delete=models.CASCADE)
    slate = models.ForeignKey(Slate, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    lock = models.BooleanField(default=False)
    remove = models.BooleanField(default=False)
    ownership = models.DecimalField(max_digits=5, decimal_places=2)
    exposure = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    projection = models.DecimalField(max_digits=5, decimal_places=2)
    
    def __str__(self):
        return f"{self.meta_player} - {self.user} - {self.slate}"


class UserOptoSettings(models.Model):

    class Meta:
        verbose_name = 'User Opto Setting'
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    max_salary = models.IntegerField(default=50000)
    min_salary = models.IntegerField(default=49000)
    max_players_per_team = models.IntegerField(default=5)
    uniques = models.IntegerField(default=3)

    def __str__(self):
        return f"{self.user} Settings"


class Optimization(models.Model):
    lineups = models.JSONField()
    exposures = models.JSONField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    slate = models.ForeignKey(Slate, on_delete=models.CASCADE)

    def __str__(self):
        return f"Optimization - {self.id}"