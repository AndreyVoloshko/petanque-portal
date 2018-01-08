from django.db import models
from django.utils import timezone
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from federation.models.player import Player

# Teams
class Team(models.Model):
    default_name = "-"

    name            = models.CharField(_('name'), max_length=150, blank=True, null=True)
    players         = models.ManyToManyField(Player, through='PlayerTeamMembership', verbose_name="Гравці")
    date_created    = models.DateTimeField(_('Дата створення'), default=timezone.now)

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        name = self.name
        if not name:
            name = self.default_name

            capitan = self.get_capitan()
            if capitan:
                name = capitan.get_name()
            elif self.players.all()[0]:
                name = self.players.all()[0].get_name()

        return "%s (%s)" % (
            name,
            ", ".join(player.get_name() for player in self.players.all()),
        )

    def get_short_name(self):
        name = self.name
        if not name:
            name = self.default_name

            capitan = self.get_capitan()
            if capitan:
                name = capitan.get_name()
            elif self.players.all()[0]:
                name = self.players.all()[0].get_name()

        return "%s" % (
            name
        )

    def get_capitan(self):
        return self.players.filter(playerteammembership__is_capitan=True).first()

    @classmethod
    def get_list_by_player(self, player):
        return self.objects.filter(playerteammembership__player=player)

    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команди'


# Players to Teams relation
class PlayerTeamMembership(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, verbose_name="Гравцi")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name="Команди")
    is_capitan = models.BooleanField(_('Капiтан'), default=False)

    class Meta:
        verbose_name = 'Належнiсть до команд'
        verbose_name_plural = 'Належнiсть до команд'

# Classes for admin
class MembershipInline(admin.TabularInline):
    model = PlayerTeamMembership
    extra = 1

    class Meta:
        verbose_name = 'Належнiсть до команд'
        verbose_name_plural = 'Належнiсть до команд'

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'surname', 'licence_number', 'gender', 'arbiter_level', 'current_club', 'birth_date', 'prefred_position', )
    search_fields = ('name', 'surname', 'current_club__name', 'arbiter_level', 'licence_number', )
    list_per_page = 25
    inlines = (MembershipInline,)

class TeamAdmin(admin.ModelAdmin):
    def team_get_full_name(self, obj):
        return obj.get_full_name()
    team_get_full_name.short_description = "Гравці"

    def team_get_capitan(self, obj):
        return obj.get_capitan()
    team_get_capitan.short_description = "Капітан"

    list_display = ('id', 'name', 'team_get_full_name', 'team_get_capitan', )
    search_fields = ('name', 'players__name', 'players__surname', )
    list_per_page = 25
    inlines = (MembershipInline,)
