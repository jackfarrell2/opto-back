from django.db import models
from pytz import timezone


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
