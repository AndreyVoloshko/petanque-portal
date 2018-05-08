from django.db import models
from django.utils import timezone
import datetime
import math

from datetime import date
import federation.config.rating as rating_config
from django.contrib import admin
from federation.storage import MediaStorage
from django.utils.translation import ugettext_lazy as _
from federation.models.player import Player
from federation.models.team import Team
from federation.admin_actions.tournament import recalculate_power, recalculate_ratings, finish_processing, erase_rating_points_and_powers, mark_as_ready_for_processing, full_power_and_rating_processing, erase_registration_dates


# Tournaments
class Tournament(models.Model):
    TYPE_CHOICES = (
        ('open', 'Вiдкритий'),
        ('fpu', 'ФПУ'),
        ('away', 'Закордонний'),
        ('other', 'Інше'),
    )

    FORMAT_CHOICES = (
        ('swiss', 'Швейцарська система'),
        ('swiko', 'Швейцарська система + На виліт'),
        ('ko', 'На виліт'),
        ('each', 'Кожен з кожним'),
        ('tir', 'Турнір з тиру'),
        ('mele', 'Супер-меле'),
    )

    name = models.CharField(_('name'), max_length=150)

    category = models.CharField(_('Категорія'), max_length=5, choices=TYPE_CHOICES)
    is_goes_to_rating = models.BooleanField(_('Рейтинговий'), default=False)
    is_ukrainian_league = models.BooleanField(_('Турнір Української Ліги Петанку'), default=False)
    is_b_tournament = models.BooleanField(_('Турнір "B"'), default=False)
    is_ready_for_processing = models.BooleanField(_('Турнір готовий до опрацювання'), default=False)

    total_number_of_teams = models.IntegerField(_('Повна кількість команд'), blank=True, null=True)

    rating_coefficient = models.FloatField(_('Рейтинговий коефіцієнт'), default=1)
    power = models.DecimalField(_('Сила турніру'), default=0, max_digits=19, decimal_places=4)

    place = models.CharField(_('Місце проведення'), max_length=500)

    start_date = models.DateField(_('Дата початку'), default=timezone.now)
    start_time = models.TimeField(_('Час початку'), default=timezone.now)
    end_date = models.DateField(_('Дата закінчення'), blank=True, null=True)

    date_registration_stop = models.DateTimeField(_('Дата закінчення реєстрації'), blank=True, null=True)
    number_of_players_in_team_min = models.IntegerField(_('Мінімальна кількість гравців в команді'), default=1)
    number_of_players_in_team_max = models.IntegerField(_('Кількість гравців в команді (з запасними)'), default=1)
    format = models.CharField(_('Формат'), max_length=5, choices=FORMAT_CHOICES)
    organizer_club = models.ForeignKey('Club', models.SET_NULL, blank=True, null=True, verbose_name="Клуб організатор")
    terms = models.FileField(_('Регламент'), blank=True, null=True, storage=MediaStorage())
    teams_limit = models.IntegerField(_('Ліміт команд'), default=100)
    fee = models.TextField(_('Внески'), blank=True, null=True)
    federation_delegat = models.ForeignKey('Player', models.SET_NULL, blank=True, null=True, verbose_name="Делегат федерації",
                                           related_name='tournament_federation_delegat')

    arbiters = models.ManyToManyField(Player, through='ArbiterTournamentMembership', related_name='tournament_arbiters', blank=True)
    teams = models.ManyToManyField(Team, through='TeamTournamentMembership', related_name='tournament_teams', blank=True)
    notes = models.TextField(_('Нотатки'), blank=True, null=True)

    is_processing_finished = models.BooleanField(_('Результати турніру опрацьовано'), default=False)

    def __str__(self):
        return self.get_name()

    def get_name(self):
        return self.name

    def get_max_players_per_team (self):
        if self.number_of_players_in_team_max:
            return self.number_of_players_in_team_max
        else:
            return self.number_of_players_in_team_min

    '''
        add team to current tournament
    '''
    def add_team(self, team):
        new_team = TeamTournamentMembership(tournament=self, team=team)
        new_team.save()

    '''
        recalculate teams power
    '''
    def recalculate_power(self):
        if self.category == 'away':
            raise Exception("Закордонні турніри не беруть участі у рейтингу")

        if not self.is_ready_for_processing:
            raise Exception("Турнір не помічено як готовий до оправцювання")

        if self.is_processing_closed():
            raise Exception("Турнір вже закритий для опрацювання!")

        teams_count = self.get_teams_count()

        if teams_count <= 0:
            raise Exception("У турнірі не зареєстровано жожної команди!")

        # recalculate all teams power
        teams = self.get_teams()
        for team in teams:
            team.recalculate_power()

        # get top teams
        teams = self.get_teams()
        top_teams_needed = rating_config.RATING_TOURNAMENT_POWER_TEAMS_COUNT
        teams = teams[:top_teams_needed]

        # calculate new tournament power
        power = 0
        for team in teams:
            power += team.power

        power = power / top_teams_needed

        # save new power
        self.power = power
        self.save()

    '''
        recalculate teams power on registration
    '''
    def recalculate_power_on_registration(self):
        if self.category == 'away':
            return False

        if self.is_processing_closed():
            return False

        teams_count = self.get_teams_count()

        if teams_count <= 0:
            return False

        # recalculate all teams power
        teams = self.get_teams()
        for team in teams:
            team.recalculate_power()

        # get top teams
        teams = self.get_teams()
        top_teams_needed = rating_config.RATING_TOURNAMENT_POWER_TEAMS_COUNT
        teams = teams[:top_teams_needed]

        # calculate new tournament power
        power = 0
        for team in teams:
            power += team.power

        power = power / top_teams_needed

        # save new power
        self.power = power
        self.save()

    '''
        Close tournament for processing and trigger player's rating recalculation
    '''
    def close_for_processing(self):
        if self.category == 'away':
            raise Exception("Закордонні турніри не беруть участі у рейтингу")

        if not self.is_ready_for_processing:
            raise Exception("Турнір не помічено як готовий до оправцювання")

        if self.is_processing_closed():
            raise Exception("Турнір вже закритий для опрацювання!")

        if not self.is_finished():
            raise Exception("Турнір ще не закінчився!")

        teams = self.get_teams()
        teams_count = self.get_teams_count()

        if teams_count <= 0:
            raise Exception("У турнірі повинна бути хоча б одна команда")

        if self.power <= 0:
            raise Exception("Сила турніру менша або дорівнює нулю. Перерахуйте її")

        self.is_processing_finished = True
        self.save()

        for team in teams:
            team.recalculate_ratings_for_players()

    '''
        recalculate teams rating points according to places
    '''
    def recalculate_ratings(self):
        if self.category == 'away':
            raise Exception("Закордонні турніри не беруть участі у рейтингу")

        if not self.is_ready_for_processing:
            raise Exception("Турнір не помічено як готовий до оправцювання")

        if self.is_processing_closed():
            raise Exception("Турнір вже закритий для опрацювання!")

        if not self.is_finished():
            raise Exception("Турнір ще не закінчився!")

        teams = self.get_teams()
        teams_count = self.get_teams_count()

        if teams_count <= 0:
            raise Exception("У турнірі повинна бути хоча б одна команда")

        if self.power <= 0:
            raise Exception("Сила турніру менша або дорівнює нулю. Перерахуйте її")

        basic_points = self.calculate_basic_points(teams_count)

        for team in teams:
            team_points = self.calculate_raw_team_rating_points(basic_points, team.place_min)

            team_rating_points = float(team_points) * self.rating_coefficient * float(self.power)

            team.rating_power = team_points
            team.rating_points = team_rating_points
            team.save()

    '''
    Return teams count
    '''
    def get_teams_count(self):
        if self.total_number_of_teams and self.total_number_of_teams > 0:
            return self.total_number_of_teams

        teams = self.get_teams()
        return teams.count()

    '''
    Reopen tournament and erase all powers and rating points
    '''
    def erase_rating_points_and_powers(self):
        if not self.is_finished():
            raise Exception("Турнір ще не закінчився!")

        teams = self.get_teams()
        teams_count = self.get_teams_count()

        if teams_count <= 0:
            raise Exception("У турнірі повинна бути хоча б одна команда")

        self.is_processing_finished = True
        self.is_ready_for_processing = False
        self.power = 0
        self.save()

        for team in teams:
            team.erase_rating_points_and_powers()

    def erase_registration_date(self):
        self.date_registration_stop = None
        self.save()


    '''
    Mark tournament as ready for processing
    '''
    def mark_as_ready_for_processing(self):
        self.is_processing_finished = False
        self.is_ready_for_processing = True
        self.save()

    '''
        calculate basic points first team gets for this tournament
    '''
    def calculate_basic_points(self, teams_count):
        basic_points = math.ceil(math.log(teams_count, 2))
        return basic_points

    '''
        calculate rating points based on basic number and team's place
    '''
    def calculate_raw_team_rating_points(self, basic_points, team_place):

        # 1st place gets basic points every time
        if team_place == 1:
            return basic_points

        # get place related to points should be calculated
        # 2 is related to 1
        # 3,4 are related to 2
        # 5-8 are related to 4 ... all of them are powers of 2
        closest_power_of_two = int(math.log(team_place, 2))

        # the place related to which current team will get points
        related_teams_place = int(math.pow(2, closest_power_of_two))

        if related_teams_place == team_place:
            closest_power_of_two -= 1
            related_teams_place = int(math.pow(2, closest_power_of_two))

        # team basic points = points of related team's place - 1
        team_basic_points = self.calculate_raw_team_rating_points(basic_points, related_teams_place)

        # now get the place team got related to related_place
        # examples:
        # 3 is number 1 related to 2nd
        # 4 is number 2 related to 2nd
        # 7 is number 3 related to 4th ...
        part_form_the_points = int(team_place % related_teams_place)
        if part_form_the_points == 0:
            part_form_the_points = related_teams_place

        # calculate team points
        team_points = team_basic_points - part_form_the_points / related_teams_place

        return team_points

    # is tournament closed for processing
    def is_processing_closed(self):
        return self.is_processing_finished

    # is tournament closed for processing
    def is_registration_opened(self):
        if self.date_registration_stop:
            return self.date_registration_stop >= timezone.now()
        else:
            return False

    # is tournament already began
    def is_began(self):
        return self.start_date < date.today()

    # is tournament already finished
    def is_finished(self):
        if not self.is_began():
            return False

        if self.end_date:
            return self.end_date < date.today()

        return True

    def get_teams(self):
        return TeamTournamentMembership.objects.filter(tournament=self).order_by('-power')

    @classmethod
    def get_list(self, date_filter=None, type_filter=None, custom_order=None):
        now = datetime.datetime.now()

        tournaments = self.objects.all()

        if date_filter == 'past':
            #tournaments = tournaments.filter(start_date__year=now.year)
            tournaments = tournaments.filter(start_date__lte=now)
        elif date_filter == 'future':
            tournaments = tournaments.filter(start_date__gte=now)
        elif date_filter and date_filter.is_integer():
            tournaments = tournaments.filter(start_date__year=date_filter)

        if type_filter == 'rating':
            tournaments = tournaments.filter(is_goes_to_rating=True)
        if type_filter == 'non_rating':
            tournaments = tournaments.exclude(category='away').filter(is_goes_to_rating=False)
        elif type_filter == 'away':
            tournaments = tournaments.filter(category='away')
        elif type_filter == 'b':
            tournaments = tournaments.filter(is_b_tournament=True)
        elif type_filter == 'liga':
            tournaments = tournaments.filter(is_ukrainian_league=True)
        elif type_filter == 'except_b':
            tournaments = tournaments.filter(is_b_tournament=False)

        order = '-start_date'
        if custom_order is not None:
            order = custom_order

        elif date_filter == 'future':
            order = 'start_date'

        return tournaments.order_by(order)

    @classmethod
    def get_list_by_dates_range(self, start_date=None, end_date=None):
        tournaments = self.objects.all()

        if start_date:
            tournaments = tournaments.filter(start_date__gte=start_date)

        if end_date:
            tournaments = tournaments.filter(start_date__lte=end_date)

        return tournaments.order_by('-start_date')

    @classmethod
    def get_list_by_player(self, player, date_filter=None, type_filter=None):
        now = datetime.datetime.now()

        tournaments = self.objects.all()

        user_teams = Team.get_list_by_player(player=player)
        tournaments = tournaments.filter(teamtournamentmembership__team__in=user_teams)

        if date_filter == 'past':
            #tournaments = tournaments.filter(start_date__year=now.year)
            tournaments = tournaments.filter(start_date__lte=now)
        elif date_filter == 'future':
            tournaments = tournaments.filter(start_date__gte=now)
        elif date_filter and date_filter.is_integer():
            tournaments = tournaments.filter(start_date__year=date_filter)

        if type_filter == 'rating':
            tournaments = tournaments.filter(is_goes_to_rating=True)
        elif type_filter == 'away':
            tournaments = tournaments.filter(category='away')
        elif type_filter == 'b':
            tournaments = tournaments.filter(is_b_tournament=True)
        elif type_filter == 'non':
            tournaments = tournaments.filter(is_goes_to_rating=False)
            tournaments = tournaments.filter(is_b_tournament=False)
        elif type_filter == 'except_b':
            tournaments = tournaments.filter(is_b_tournament=False).exclude(category="away")

        return tournaments.order_by('-start_date')

    def get_team_which_contains_player(self, player):
        user_teams = Team.get_list_by_player(player=player)
        try:
            user_tournament_team = TeamTournamentMembership.objects.get(tournament=self, team__in=user_teams)
        except TeamTournamentMembership.DoesNotExist:
            user_tournament_team = None

        return user_tournament_team


    class Meta:
        verbose_name = 'Турнір'
        verbose_name_plural = 'Турніри'


# Teams to Tournaments relation
class TeamTournamentMembership(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, verbose_name="Турнір")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name="Команда")
    place_min = models.IntegerField(_('Місце'), default=0)
    place_max = models.IntegerField(_('Місце (максимальне)'), default=0)
    date_registration = models.DateField(_('Дата реєстрації'), default=timezone.now)

    rating_points = models.DecimalField(_('Рейтингові пункти за турнір'), default=0, max_digits=19, decimal_places=4)
    rating_power = models.DecimalField(_('Рейтингова сила за турнір'), default=0, max_digits=19, decimal_places=4)

    power = models.DecimalField(_('Сила команди'), default=0, max_digits=19, decimal_places=4)

    def recalculate_power(self):
        power = 0
        for player in self.team.players.all():
            if self.tournament.is_b_tournament:
                power += player.current_power_b
            else:
                power += player.current_power

        power = power / self.team.players.count()
        self.power = power
        self.save()

    def recalculate_ratings_for_players(self):
        for player in self.team.players.all():
            player.recalculate_ratings()

    def erase_rating_points_and_powers(self):
        self.rating_points = 0
        self.rating_power = 0
        self.power = 0
        self.save()

    class Meta:
        verbose_name = 'Команди турніру'
        verbose_name_plural = 'Команди турніру'


# Arbiters to Tournaments relation
class ArbiterTournamentMembership(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, verbose_name="Турнір")
    arbiter = models.ForeignKey(Player, on_delete=models.CASCADE, verbose_name="Арбітр")
    is_main_arbiter = models.BooleanField(_('Головний арбітр'), default=False)

    class Meta:
        verbose_name = 'Арбітри турніру'
        verbose_name_plural = 'Арбітри турніру'


# Classes for admin
class ArbiterTournamentMembershipInline(admin.TabularInline):
    model = ArbiterTournamentMembership
    extra = 0

    class Meta:
        verbose_name = 'Арбітри турніру'
        verbose_name_plural = 'Арбітри турніру'


# Classes for admin
class TeamsTournamentMembershipInline(admin.TabularInline):
    model = TeamTournamentMembership
    extra = 0

    class Meta:
        verbose_name = 'Команди турніру'
        verbose_name_plural = 'Команди турніру'


class ArbiterTeamTournamentAdminInline(admin.ModelAdmin):
    inlines = (ArbiterTournamentMembershipInline,TeamsTournamentMembershipInline,)
    search_fields = (
        'id',
        'name',
        'category',
        'organizer_club__name',
        'number_of_players_in_team_min',
        'is_goes_to_rating',
        'is_ukrainian_league',
        'is_b_tournament'
    )
    list_per_page = 25
    list_display = [
        'id',
        'name',
        'start_date',
        'category',
        'power',
        'rating_coefficient',
        'is_goes_to_rating',
        'is_ukrainian_league',
        'is_b_tournament',
        'is_ready_for_processing',
        'is_processing_finished',
    ]

    actions = [recalculate_power,
               recalculate_ratings,
               finish_processing,
               erase_rating_points_and_powers,
               mark_as_ready_for_processing,
               full_power_and_rating_processing,
               erase_registration_dates]