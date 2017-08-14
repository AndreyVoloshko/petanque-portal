from django.contrib import admin
from .models.city import City
from .models.club import Club
from .models.player import Player
from .models.team import Team, TeamAdmin, PlayerAdmin
from .models.tournament import Tournament, ArbiterTeamTournamentAdminInline

# Register your models here.
admin.site.register(City)
admin.site.register(Club)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Tournament, ArbiterTeamTournamentAdminInline)
