from django.contrib import admin
from django.contrib.admin.models import LogEntry

from .models.city import City
from .models.club import Club, ClubAdmin, CityAdmin
from .models.player import Player
from .models.team import Team, TeamAdmin, PlayerAdmin
from .models.tournament import Tournament, ArbiterTeamTournamentAdminInline
from .models.national_teams import National_team, National_teamAdmin
from .models.record import Record
from .models.document import Document, DocumentCategory
from .models.season import Season, SeasonAdmin
from .models.department import Department, DepartmentAdmin
from .models.email_confirmation import EmailConfirmation
from .player_change_log_admin import AuditLogAdmin
from .audit_admin import RevertibleAuditAdminMixin


class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)
    ordering = ('order', 'name')


class DocumentAdmin(RevertibleAuditAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'category', 'document_date', 'download_count', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'notes')
    readonly_fields = ('download_count', 'created_at')
    ordering = ('-document_date', '-created_at')


# Register your models here.
admin.site.register(City, CityAdmin)
admin.site.register(Club, ClubAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Tournament, ArbiterTeamTournamentAdminInline)
admin.site.register(National_team, National_teamAdmin)
admin.site.register(Record)
admin.site.register(DocumentCategory, DocumentCategoryAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(Season, SeasonAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(EmailConfirmation)
admin.site.register(LogEntry, AuditLogAdmin)
