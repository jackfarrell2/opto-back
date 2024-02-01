from django.contrib import admin
from .models import Slate, Team, Player, Game, UserPlayer, UserOptoSettings

admin.site.register(Slate)
admin.site.register(Team)
admin.site.register(Player)
admin.site.register(Game)
admin.site.register(UserPlayer)
admin.site.register(UserOptoSettings)
