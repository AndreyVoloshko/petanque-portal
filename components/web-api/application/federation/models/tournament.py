from django.db import models
from django.utils import timezone
import datetime
from django.contrib import admin
from federation.storage import AvatarsStorage
from django.utils.translation import ugettext_lazy as _
from federation.models.player import Player
from federation.models.team import Team
from federation.admin_actions.tournament import recalculate_power, recalculate_ratings, finish_processing

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
        ('mele', 'Супер-меле'),
    )

    name = models.CharField(_('name'), max_length=150)

    category = models.CharField(_('Категорія'), max_length=5, choices=TYPE_CHOICES)
    is_goes_to_rating = models.BooleanField(_('Рейтинговий'), default=False)
    is_ukrainian_league = models.BooleanField(_('Турнір Української Ліги Петанку'), default=False)
    is_b_tournament = models.BooleanField(_('Турнір "B"'), default=False)
    is_processing_finished = models.BooleanField(_('Результати турніру опрацьовано'), default=False)

    total_number_of_teams = models.IntegerField(_('Повна кількість команд'), blank=True, null=True)

    rating_coefficient = models.FloatField(_('Рейтинговий коефіцієнт'), default=1)
    power = models.FloatField(_('Сила турніру'), default=1)

    place = models.CharField(_('Місце проведення'), max_length=500)

    start_date = models.DateField(_('Дата початку'), default=timezone.now)
    start_time = models.TimeField(_('Час початку'), default=timezone.now)
    end_date = models.DateField(_('Дата закінчення'), blank=True, null=True)

    date_registration_stop = models.DateTimeField(_('Дата закінчення реєстрації'), default=timezone.now)
    number_of_players_in_team_min = models.IntegerField(_('Мінімальна кількість гравців в команді'), default=1)
    number_of_players_in_team_max = models.IntegerField(_('Кількість гравців в команді (з запасними)'), default=1)
    format = models.CharField(_('Формат'), max_length=5, choices=FORMAT_CHOICES)
    organizer_club = models.ForeignKey('Club', models.SET_NULL, blank=True, null=True, verbose_name="Клуб організатор")
    terms = models.FileField(_('Регламент'), blank=True, null=True, storage=AvatarsStorage())
    teams_limit = models.IntegerField(_('Ліміт команд'), default=100)
    fee = models.TextField(_('Внески'), blank=True, null=True)
    federation_delegat = models.ForeignKey('Player', models.SET_NULL, blank=True, null=True, verbose_name="Делегат федерації",
                                           related_name='tournament_federation_delegat')

    arbiters = models.ManyToManyField(Player, through='ArbiterTournamentMembership', related_name='tournament_arbiters', blank=True)
    teams = models.ManyToManyField(Team, through='TeamTournamentMembership', related_name='tournament_teams', blank=True)
    notes = models.TextField(_('Нотатки'), blank=True, null=True)

    def __str__(self):
        return self.get_name()

    def get_name(self):
        return self.name

    @classmethod
    def get_list(self, date_filter=None, type_filter=None):
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
        elif type_filter == 'away':
            tournaments = tournaments.filter(category='away')
        elif type_filter == 'b':
            tournaments = tournaments.filter(is_b_tournament=True)
        elif type_filter == 'non':
            tournaments = tournaments.filter(is_goes_to_rating=False)
            tournaments = tournaments.filter(is_b_tournament=False)
        elif type_filter == 'except_b':
            tournaments = tournaments.filter(is_b_tournament=False)

        return tournaments.order_by('-start_date')

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
            tournaments = tournaments.filter(is_b_tournament=False)

        return tournaments.order_by('-start_date')

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
    rating_points = models.IntegerField(_('Рейтингові пункти за турнір'), default=0)
    power = models.IntegerField(_('Сила команди'), default=0)

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
        'is_processing_finished',
    ]

    actions = [recalculate_power, recalculate_ratings, finish_processing]