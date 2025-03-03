from django.contrib import admin
from .models.city import City
from .models.club import Club, ClubAdmin, CityAdmin
from .models.player import Player
from .models.team import Team, TeamAdmin, PlayerAdmin
from .models.tournament import Tournament, ArbiterTeamTournamentAdminInline
from .models.national_teams import National_team, National_teamAdmin
from .models.record import Record
from .models.document import Document
from .models.season import Season, SeasonAdmin
from .models.department import Department, DepartmentAdmin

# Register your models here.
admin.site.register(City, CityAdmin)
admin.site.register(Club, ClubAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Tournament, ArbiterTeamTournamentAdminInline)
admin.site.register(National_team, National_teamAdmin)
admin.site.register(Record)
admin.site.register(Document)
admin.site.register(Season, SeasonAdmin)
admin.site.register(Department, DepartmentAdmin)