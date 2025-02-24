from django.db import models
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from federation.models.player import Player

# Clubs
class National_team (models.Model):
    default_name = "-"

    name = models.CharField(_('Повна назва команди'), max_length=150)
    players = models.ManyToManyField(Player, through='PlayerNational_teamMembership', verbose_name="Гравці")

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        name = self.name
        if not name:
            name = self.default_name

        return "%s (%s)" % (
            name,
            ", ".join(player.get_name() for player in self.players.all()),
        )

    class Meta:
        verbose_name = 'Збірна команди'
        verbose_name_plural = 'Збірнi команди'

# Players to Teams relation
class PlayerNational_teamMembership(models.Model):
    POSITIONS = (
        ('player', 'Гравець'),
        ('coach', 'Тренер'),
        ('main_coach', 'Головний тренер'),
        ('capitan', 'Капітан'),
        ('selection', 'Основний склад'),
    )

    player = models.ForeignKey(Player, on_delete=models.CASCADE, verbose_name="Гравцi", null=True)
    team = models.ForeignKey(National_team, on_delete=models.CASCADE, verbose_name="Команди", null=True)
    position = models.CharField(_('Позиція'), max_length=50, choices=POSITIONS)

    class Meta:
        verbose_name = 'Належнiсть до команд'
        verbose_name_plural = 'Належнiсть до команд'



# Classes for admin
class MembershipInline(admin.TabularInline):
    model = PlayerNational_teamMembership
    extra = 1

    class Meta:
        verbose_name = 'Належнiсть до команд'
        verbose_name_plural = 'Належнiсть до команд'


class National_teamAdmin(admin.ModelAdmin):
    def team_get_full_name(self, obj):
        return obj.get_full_name()
    team_get_full_name.short_description = "Гравці"

    list_display = ('id', 'name', 'team_get_full_name', )
    search_fields = ('name', 'city__name', )
    list_per_page = 25
    inlines = (MembershipInline,)
    autocomplete_fields = ['players__player']

