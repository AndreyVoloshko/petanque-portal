from datetime import datetime, timedelta
from django.db import models
from django_countries.fields import CountryField
from django.contrib.auth.models import User
from federation.storage import MediaStorage
from django.utils.translation import ugettext_lazy as _
import federation.config.rating as rating_config
from federation.helpers.general import get_model
from django.conf import settings


# Players
class Player(models.Model):
    GENDER_CHOICES = (
        ('M', 'Чоловiк'),
        ('F', 'Жiнка'),
    )

    ARBITER_CATEGORY = (
        ('club', 'Друга категорія'),
        ('regional', 'Перша категорія'),
        ('national', 'Національний'),
        ('euro', 'Арбітр CEP (Європейський)'),
        ('fipjp', 'Арбітр FIPJP (Міжнародний)'),
    )

    COACH_CATEGORY = (
        ('A', 'A (Аніматор)'),
        ('I1', 'I1 (Інструктор 1-ої категорії)'),
        ('I2', 'I2 (Інструктор 2-ої категорії)'),
        ('I3', 'I3 (Інструктор 3-ої категорії)'),
        ('I4', 'I4 (Інструктор 4-ої категорії)'),
        ('E1', 'E1 (Тренер-інструктор 1-ої категорії)'),
        ('E2', 'E2 (Тренер-інструктор 2-ої категорії)'),
        ('E3', 'E3 (Тренер-інструктор 3-ої категорії)'),
        ('E4', 'E4 (Тренер-інструктор 4-ої категорії)')
    )

    POSITIONS = (
        ('point', 'Поінтер'),
        ('middle', 'Мідл'),
        ('shooter', 'Шутер'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    avatar = models.ImageField(_('avatar'), blank=True, null=True, storage=MediaStorage())
    name = models.CharField(_('name'), max_length=100)
    surname = models.CharField(_('Прізвищє'), max_length=100)
    birth_date = models.DateField(_('Дата народження'))
    current_club = models.ForeignKey('Club', models.SET_NULL, blank=True, null=True, verbose_name="Клуб")
    country = CountryField(blank_label=_('(select country)'), verbose_name="Країна")
    licence_number = models.CharField(_('Номер ліцензії'), max_length=50, blank=True, null=True)
    gender = models.CharField(_('Стать'), max_length=1, choices=GENDER_CHOICES)
    prefred_position = models.CharField(_('Позиція'), max_length=10, choices=POSITIONS, blank=True, null=True)

    facebook = models.CharField(_('facebook'), max_length=500, blank=True, null=True)
    twitter = models.CharField(_('twitter'), max_length=500, blank=True, null=True)
    instagram = models.CharField(_('instagram'), max_length=500, blank=True, null=True)
    website  = models.CharField(_('website'), max_length=500, blank=True, null=True)

    arbiter_level = models.CharField(_('Рівень арбітражу'), max_length=10, choices=ARBITER_CATEGORY, blank=True, null=True)
    coach_level = models.CharField(_('Тренерська категорія'), max_length=20, choices=COACH_CATEGORY, blank=True, null=True)

    current_rating = models.DecimalField(_('Поточні рейтингові пункти'), default=0, max_digits=19, decimal_places=4)
    current_rating_b = models.DecimalField(_('Поточні рейтингові пункти у турнірах "B'), default=0, max_digits=19, decimal_places=4)
    current_rating_liga = models.DecimalField(_('Поточні рейтингові пункти у турнірах "Ліги"'), default=0, max_digits=19, decimal_places=4)

    current_power = models.DecimalField(_('Поточна сила'), default=0, max_digits=19, decimal_places=4)
    current_power_b = models.DecimalField(_('Поточна сила у турнірах "B'), default=0, max_digits=19,
                                           decimal_places=4)
    '''
    Erase all rating points for player
    '''
    def erase_ratings(self):
        self.current_rating = 0
        self.current_rating_b = 0
        self.current_rating_liga = 0
        self.save()

    '''
    Erase licence number
    '''
    def erase_licence_number(self):
        self.licence_number = None
        self.save()

    '''
    Ranking among licensed players
    '''
    def get_ranking(self, ranking='current_rating', players_objects=None):
        if players_objects is None:
            players_objects = self.get_actual_players_list()

        return players_objects.filter(**{
            ranking + "__gt" : getattr(self, ranking)
        }).count() + 1

    '''
    Actual licensed players list
    '''
    @classmethod
    def get_actual_players_list(self):
        '''
        return Player.objects.filter(country=settings.CURRENT_COUNTRY)\
                .exclude(licence_number="")\
                .exclude(licence_number__isnull=True)
        '''
        return Player.objects.all().exclude(licence_number="").exclude(licence_number__isnull=True)

    '''
    Ranking among all players including non-licensed
    '''
    def get_ranking_among_all(self, ranking='current_rating'):
        #return self.get_ranking(ranking, Player.objects.filter(country=settings.CURRENT_COUNTRY))
        return self.get_ranking(ranking, Player.objects.all())

    def recalculate_ratings(self):
        if not self.licence_number:
            self.erase_ratings()
            return

        # recalculate tournaments
        tournaments_model = get_model('Tournament')
        all_past_tournaments = tournaments_model.get_list_by_player(player=self, date_filter='past')

        # filter last tournaments
        last_period_days = 30 * rating_config.RATING_PLAYER_POWER_PAST_MONTHES
        last_period = datetime.today() - timedelta(days=last_period_days)

        all_past_tournaments = all_past_tournaments.filter(start_date__gte=last_period, is_processing_finished=True)

        new_points_for_rating = []
        new_points_for_rating_b = []
        new_points_for_rating_liga = []

        new_power_for_rating = []
        new_power_for_rating_b = []

        for tournament in all_past_tournaments:
            player_team = tournament.get_team_which_contains_player(self)

            if tournament.is_goes_to_rating:
                new_points_for_rating.append(player_team.rating_points)
                new_power_for_rating.append(player_team.rating_power)

            if tournament.is_b_tournament:
                new_points_for_rating_b.append(player_team.rating_points)
                new_power_for_rating_b.append(player_team.rating_power)

        top_tournaments_number = rating_config.RATING_PLAYER_POWER_TOURNAMENTS_COUNT

        rating_points = sum(
            sorted(new_points_for_rating, reverse=True)[:top_tournaments_number]
        )
        b_rating_points = sum(
            sorted(new_points_for_rating_b, reverse=True)[:top_tournaments_number]
        )
        rating_power = sum(
            sorted(new_power_for_rating, reverse=True)[:top_tournaments_number]
        )
        b_rating_power = sum(
            sorted(new_power_for_rating_b, reverse=True)[:top_tournaments_number]
        )

        if not self.licence_number:
            rating_points = 0
            b_rating_points = 0
            rating_power = 0
            b_rating_power = 0

        self.current_power = rating_points
        self.current_power_b = b_rating_power
        self.current_rating = rating_points
        self.current_rating_b = b_rating_points
        self.save()


    def __str__(self):
        return self.get_name()

    def get_name(self):
        return self.surname.upper() + " " +self.name

    @classmethod
    def get_by_name_and_surname(self, name, surname):
        try:
            player = Player.objects.get(name__iexact=name, surname__iexact=surname)
            if player:
                return player

            player = Player.objects.get(name__iexact=surname, surname__iexact=name)

        except Exception:
            player = None

        return player

    class Meta:
        verbose_name = 'Гравець'
        verbose_name_plural = 'Гравці'
