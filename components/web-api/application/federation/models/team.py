from django.db import models
from django.utils import timezone
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from federation.models.player import Player

# Teams
class Team(models.Model):
    default_name = "-"

    name            = models.CharField(_('name'), max_length=150, blank=True, null=True)
    players         = models.ManyToManyField(Player, through='PlayerTeamMembership')
    date_created    = models.DateTimeField(_('date_created'), default=timezone.now)

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        name = self.name
        if not name:
            name = self.default_name

            capitan = self.get_capitan()
            if capitan:
                name = capitan.get_name()

        return "%s (%s)" % (
            name,
            ", ".join(player.get_name() for player in self.players.all()),
        )

    def get_capitan(self):
        return self.players.filter(playerteammembership__is_capitan=True).first()

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
    inlines = (MembershipInline,)

class TeamAdmin(admin.ModelAdmin):
    inlines = (MembershipInline,)
