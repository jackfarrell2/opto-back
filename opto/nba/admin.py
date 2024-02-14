from django.contrib import admin
from .models import Slate, Team, Player, Game, UserPlayer, UserOptoSettings, Optimization, IgnoreOpto

admin.site.register(Slate)
admin.site.register(Team)
admin.site.register(Player)
admin.site.register(Game)
admin.site.register(UserPlayer)
admin.site.register(UserOptoSettings)
admin.site.register(Optimization)
admin.site.register(IgnoreOpto)
