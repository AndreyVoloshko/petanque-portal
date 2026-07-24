import datetime
from django.db import models
from django.contrib import admin
from federation.admin_mixins import RestrictedRelatedWidgetAdminMixin
from federation.helpers.general import get_model
from federation.admin_actions.seasons import save_current_ratings
from django.utils.translation import gettext_lazy as _


# Season
class Season (models.Model):

    player = models.ForeignKey('Player', verbose_name="Гравець", on_delete=models.SET_NULL, null=True)
    club = models.ForeignKey('Club', blank=True, verbose_name="Клуб", on_delete=models.SET_NULL, null=True)

    year = models.IntegerField(_('Year'), default=0)

    rating = models.DecimalField(_('Rating points'), default=0, max_digits=19, decimal_places=4)
    rating_b = models.DecimalField(_('Rating points in B tournaments'), default=0, max_digits=19,
                                           decimal_places=4)
    rating_liga = models.DecimalField(_('Rating points in League tournaments'), default=0,
                                              max_digits=19, decimal_places=4)

    def get_ranking(self, year, rating_field):
        season_model = get_model('Season')
        objects = season_model.objects.filter(year=year)

        return objects.filter(**{
            rating_field + "__gt" : getattr(self, rating_field)
        }).count() + 1


    def save_current_ratings(self):

        player_model = get_model('Player')
        season_model = get_model('Season')

        today = datetime.datetime.now()
        current_year = today.year

        players = player_model.get_actual_players_list()

        for player in players:
            try:
                existing_item = season_model.objects.get(year=current_year, player=player)
            except Exception:
                existing_item = None

            if existing_item:
                # update existing item
                existing_item.club = player.current_club
                existing_item.rating = player.current_rating
                existing_item.rating_b = player.current_rating_b
                existing_item.rating_liga = player.current_rating_liga

                existing_item.save()
            else:
                # create new item
                new_item = Season()
                new_item.year = current_year
                new_item.player = player
                new_item.club = player.current_club
                new_item.rating = player.current_rating
                new_item.rating_b = player.current_rating_b
                new_item.rating_liga = player.current_rating_liga

                new_item.save(force_insert=True)

        return True

    class Meta:
        verbose_name = 'Сезони'
        verbose_name_plural = 'Сезони'


class SeasonAdmin(RestrictedRelatedWidgetAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'year', 'player', 'club', 'rating', 'rating_b', 'rating_liga')
    search_fields = ('year', 'player__name', 'player__surname', )
    actions = [save_current_ratings, ]
    list_per_page = 25

