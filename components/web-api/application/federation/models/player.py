from datetime import datetime, timedelta
from django.db import models
from django_countries.fields import CountryField
from django.contrib.auth.models import User
from federation.storage import MediaStorage
from django.utils.translation import gettext_lazy as _
import federation.config.rating as rating_config
from federation.helpers.general import get_model
from django.conf import settings
import json


# Players
class Player(models.Model):
    GENDER_CHOICES = (
        ('M', _('Man')),
        ('F', _('Woman')),
    )

    ARBITER_CATEGORY = (
        ('junior', _('Junior sports arbiter')),
        ('arbiter', _('Ukrainian Petanque Federation arbiter')),
        ('club', _('Sports arbiter, category II')),
        ('regional', _('Sports arbiter, category I')),
        ('national', _('National category sports arbiter')),
        ('euro', _('CEP arbiter (European category)')),
        ('fipjp', _('FIPJP arbiter (world category)')),
    )

    COACH_CATEGORY = (
        ('A', _('A (Animator)')),
        ('I1', _('I1 (Instructor, category 1)')),
        ('I2', _('I2 (Instructor, category 2)')),
        ('I3', _('I3 (Instructor, category 3)')),
        ('I4', _('I4 (Instructor, category 4)')),
        ('E1', _('E1 (Coach-instructor, category 1)')),
        ('E2', _('E2 (Coach-instructor, category 2)')),
        ('E3', _('E3 (Coach-instructor, category 3)')),
        ('E4', _('E4 (Coach-instructor, category 4)'))
    )
    
    SPORT_TITLES = (
        ('candidate', _('Candidate Master of Sports of Ukraine')),
        ('master', _('Master of Sports of Ukraine')),
        ('master_sport', _('International Class Master of Sports')),
        ('honored_master_sport', _('Honored Master of Sports of Ukraine')),
    )

    POSITIONS = (
        ('point', _('Pointer')),
        ('middle', _('Middle')),
        ('shooter', _('Shooter')),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    avatar = models.ImageField(_('avatar'), blank=True, null=True, storage=MediaStorage())
    name = models.CharField(_('name'), max_length=100)
    surname = models.CharField(_('Last name'), max_length=100)
    second_name = models.CharField(_('Middle name'), max_length=100, blank=True, null=True)
    birth_date = models.DateField(_('Date of birth'))
    current_club = models.ForeignKey('Club', blank=True, verbose_name="Клуб", on_delete=models.SET_NULL, null=True)
    country = CountryField(blank_label=_('(select country)'), verbose_name="Країна", default=settings.CURRENT_COUNTRY)

    licence_number = models.CharField(_('License number'), max_length=50, blank=True, null=True)
    is_licence_active = models.BooleanField(_('License active'), default=False)

    is_inclusive = models.BooleanField(_('Inclusive player'), default=False)

    gender = models.CharField(_('Gender'), max_length=1, choices=GENDER_CHOICES)
    prefred_position = models.CharField(_('Position'), max_length=10, choices=POSITIONS, blank=True, null=True)

    facebook = models.CharField(_('facebook'), max_length=500, blank=True, null=True)
    twitter = models.CharField(_('twitter'), max_length=500, blank=True, null=True)
    instagram = models.CharField(_('instagram'), max_length=500, blank=True, null=True)
    website  = models.CharField(_('website'), max_length=500, blank=True, null=True)

    arbiter_level = models.CharField(_('Arbitration level'), max_length=10, choices=ARBITER_CATEGORY, blank=True, null=True)
    coach_level = models.CharField(_('Coach category'), max_length=20, choices=COACH_CATEGORY, blank=True, null=True)
    sport_title = models.CharField(_('Sports title'), max_length=100, blank=True, null=True, choices=SPORT_TITLES)

    current_rating = models.DecimalField(_('Current rating points'), default=0, max_digits=19, decimal_places=4)
    current_rating_b = models.DecimalField(_('Current rating points in B tournaments'), default=0, max_digits=19, decimal_places=4)
    current_rating_inclusive = models.DecimalField(_('Current rating points in inclusive tournaments'), default=0, max_digits=19, decimal_places=4)
    current_rating_liga = models.DecimalField(_('Current rating points in League tournaments'), default=0, max_digits=19, decimal_places=4)

    current_rating_tournaments = models.TextField(_('Tournaments affecting current rating'), blank=True, null=True)
    current_rating_b_tournaments = models.TextField(_('Tournaments affecting current rating in B tournaments'), blank=True, null=True)
    current_rating_inclusive_tournaments = models.TextField(_('Tournaments affecting current rating in inclusive tournaments'), blank=True, null=True)

    current_power = models.DecimalField(_('Current power'), default=0, max_digits=19, decimal_places=4)
    current_power_b = models.DecimalField(_('Current power in B tournaments'), default=0, max_digits=19,
                                           decimal_places=4)
    current_power_inclusive = models.DecimalField(_('Current power in inclusive tournaments'), default=0, max_digits=19,
                                           decimal_places=4)

    '''
    Erase all rating points for player
    '''
    def erase_ratings(self):
        self.current_rating = 0
        self.current_rating_b = 0
        self.current_rating_liga = 0
        self.current_rating_inclusive = 0
        self.save()

    '''
    Erase licence number
    '''
    def erase_licence_number(self):
        self.licence_number = None
        self.is_licence_active = False
        self.save()

    '''
    Activate licence
    '''
    def activate_licence(self):
        self.is_licence_active = True
        self.save()

    '''
    Deactivate licence
    '''
    def deactivate_licence(self):
        self.is_licence_active = False
        self.save()

    '''
    Ranking among licensed players
    '''
    def get_ranking(self, ranking='current_rating', players_objects=None):
        if players_objects is None:
            players_objects = self.get_actual_players_list()

        if ranking == 'current_rating_inclusive':
            players_objects = Player.objects.filter(is_inclusive=True)

        return players_objects.filter(**{
            ranking + "__gt" : getattr(self, ranking)
        }).count() + 1

    '''
    Actual licensed players list
    '''
    @classmethod
    def get_actual_players_list(self):
        return (
            Player.objects
            .filter(is_licence_active=True)
            .exclude(licence_number__isnull=True)
            .exclude(licence_number='')
        )

    '''
    Ranking among all players including non-licensed
    '''
    def get_ranking_among_all(self, ranking='current_rating'):
        return self.get_ranking(ranking, Player.objects.all())

    def recalculate_ratings(self):
        if not self.is_licence_active and not self.is_inclusive:
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
        new_points_for_rating_inclusive = []

        new_power_for_rating = []
        new_power_for_rating_b = []
        new_power_for_rating_inclusive = []

        for tournament in all_past_tournaments:
            player_team = tournament.get_team_which_contains_player(self)

            if tournament.is_goes_to_rating:
                new_points_for_rating.append({
                    "points": float(player_team.rating_points),
                    "tournament": tournament.pk
                })
                new_power_for_rating.append(player_team.rating_power)

            if tournament.is_b_tournament:
                new_points_for_rating_b.append({
                    "points": float(player_team.rating_points),
                    "tournament": tournament.pk
                })
                new_power_for_rating_b.append(player_team.rating_power)

            if tournament.is_inclusive:
                new_points_for_rating_inclusive.append({
                    "points": float(player_team.rating_points),
                    "tournament": tournament.pk
                })
                new_power_for_rating_inclusive.append(player_team.rating_power)

        top_tournaments_number = rating_config.RATING_PLAYER_POWER_TOURNAMENTS_COUNT

        new_points_for_rating = sorted(new_points_for_rating, key=lambda x: x['points'], reverse=True)[:top_tournaments_number]
        new_points_for_rating_b = sorted(new_points_for_rating_b, key=lambda x: x['points'], reverse=True)[:top_tournaments_number]
        new_points_for_rating_inclusive = sorted(new_points_for_rating_inclusive, key=lambda x: x['points'], reverse=True)[:top_tournaments_number]

        rating_points = sum(x['points'] for x in new_points_for_rating)
        b_rating_points = sum(x['points'] for x in new_points_for_rating_b)
        inclusive_rating_points = sum(x['points'] for x in new_points_for_rating_inclusive)

        rating_power = sum(
            sorted(new_power_for_rating, reverse=True)[:top_tournaments_number]
        )
        b_rating_power = sum(
            sorted(new_power_for_rating_b, reverse=True)[:top_tournaments_number]
        )
        inclusive_rating_power = sum(
            sorted(new_power_for_rating_inclusive, reverse=True)[:top_tournaments_number]
        )

        if not self.is_licence_active:
            rating_points = 0
            b_rating_points = 0
            rating_power = 0
            b_rating_power = 0

        self.current_rating_tournaments = json.dumps(new_points_for_rating)
        self.current_rating_b_tournaments = json.dumps(new_points_for_rating_b)
        self.current_rating_inclusive_tournaments = json.dumps(new_points_for_rating_inclusive)

        self.current_power = rating_power
        self.current_power_b = b_rating_power
        self.current_power_inclusive = inclusive_rating_power

        self.current_rating = rating_points
        self.current_rating_b = b_rating_points
        self.current_rating_inclusive = inclusive_rating_points
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
