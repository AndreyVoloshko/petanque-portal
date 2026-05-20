from django.db import models
from django.db.models import Count
from django.utils import timezone
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from federation.models.player import Player
from federation.admin_actions.player import recalculate_ratings,erase_ratings,erase_licence_number,activate_licence,deactivate_licence

# Teams
class Team(models.Model):
    default_name = "-"

    name            = models.CharField(_('name'), max_length=1000, blank=True, null=True)
    admin_name      = models.CharField("Назва в адмiн панелi", max_length=1000, blank=True, null=True)
    players         = models.ManyToManyField(Player, through='PlayerTeamMembership', verbose_name="Гравці")
    date_created    = models.DateTimeField(_('Creation date'), default=timezone.now)

    def __str__(self):
        return self.get_default_name_for_admin()

    def get_default_name_for_admin(self):
        name = self.admin_name
        if not name:
            name = self.get_full_name()
            self.admin_name = name
            self.save()

        return name

    def get_full_name(self):
        name = self.name
        if not name:
            try:
                name = self.default_name

                capitan = self.get_capitan()
                if capitan:
                    name = capitan.get_name()
                elif self.players.all()[0]:
                        name = self.players.all()[0].get_name()
            except:
                name = "Помилка, в команді немає гравців"

        return "%s: %s (%s)" % (
            self.pk,
            name,
            ", ".join(player.get_name() for player in self.players.all()),
        )

    def get_short_name(self):
        name = self.name
        if not name:
            try:
                name = self.default_name

                capitan = self.get_capitan()
                if capitan:
                    name = capitan.get_name()
                elif self.players.all()[0]:
                    name = self.players.all()[0].get_name()
            except:
                name = "Помилка, в команді немає гравців"

        return "%s" % (
            name
        )

    def get_capitan(self):
        return self.players.filter(playerteammembership__is_capitan=True).first()

    def set_capitan(self, player_id):
        PlayerTeamMembership.objects.filter(team=self).update(is_capitan=False)

        if player_id:
            PlayerTeamMembership.objects.filter(team=self, player_id=player_id).update(is_capitan=True)

    @classmethod
    def get_list_by_player(cls, player):
        return cls.objects.filter(playerteammembership__player=player)

    @classmethod
    def get_or_create_for_players(cls, player_ids):
        capitan_id = player_ids[0] if len(player_ids) > 0 else None
        team = cls.objects.annotate(players_count=Count('players')).filter(players_count=len(player_ids))

        for player_id in player_ids:
            team = team.filter(players__pk=player_id)

        if capitan_id:
            team_with_capitan = team.filter(
                playerteammembership__player_id=capitan_id,
                playerteammembership__is_capitan=True,
            ).first()

            if team_with_capitan:
                return team_with_capitan

            for existing_team in team:
                if not existing_team.get_capitan():
                    existing_team.set_capitan(capitan_id)
                    return existing_team
        else:
            existing_team = team.first()
            if existing_team:
                return existing_team

        #
        # create new team
        #
        new_team = cls()
        new_team.save()

        for player_id in player_ids:
            team_member = PlayerTeamMembership(team=new_team, player=Player.objects.get(pk=player_id))
            team_member.is_capitan = player_id == capitan_id if capitan_id else False
            team_member.save()

        return new_team

    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команди'


# Players to Teams relation
class PlayerTeamMembership(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, verbose_name="Гравцi", null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name="Команди", null=True)
    is_capitan = models.BooleanField(_('Captain'), default=False)

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
    list_display = ('id', 'name', 'surname', 'licence_number', 'is_licence_active', 'current_club', 'current_rating', 'current_rating_b', 'current_rating_inclusive', 'arbiter_level', 'coach_level')
    search_fields = ('name', 'surname', 'current_club__name', 'arbiter_level', 'licence_number', )
    list_per_page = 25
    # inlines = (MembershipInline,)
    actions = [recalculate_ratings,erase_ratings,erase_licence_number,activate_licence,deactivate_licence]
    autocomplete_fields = ['current_club', 'user']

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
