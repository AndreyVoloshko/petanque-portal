from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(City)
admin.site.register(Club)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Tournament, ArbiterTeamTournamentAdminInline)