from django.contrib import admin
from .models import Slate, Team, Player, Game, UserPlayer

admin.site.register(Slate)
admin.site.register(Team)
admin.site.register(Player)
admin.site.register(Game)
admin.site.register(UserPlayer)
