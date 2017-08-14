from django.db import models
from django.utils import timezone
from django.contrib import admin
from federation.storage import AvatarsStorage
from django.utils.translation import ugettext_lazy as _
from federation.models.player import Player
from federation.models.team import Team

# Tournaments
class Tournament(models.Model):
    TYPE_CHOICES = (
        ('open', 'Вiдктитий'),
        ('fpu', 'ФПУ'),
        ('away', 'Закордонний'),
    )

    FORMAT_CHOICES = (
        ('swiss', 'Швейцарська система'),
        ('swiko', 'Швейцарська система + На виліт'),
        ('ko', 'На виліт'),
        ('each', 'Кожен з кожним'),
    )

    name = models.CharField(_('name'), max_length=150)
    category = models.CharField(_('Категорія'), max_length=5, choices=TYPE_CHOICES)
    is_b_tournament = models.BooleanField(_('Турнір "B"'), default=False)
    is_goes_to_rating = models.BooleanField(_('Рейтинговий'), default=False)
    rating_coefficient = models.FloatField(_('Рейтинговий коефіцієнт'), default=1)
    place = models.CharField(_('Місце проведення'), max_length=500)
    start_date = models.DateField(_('Дата початку'), default=timezone.now)
    start_time = models.TimeField(_('Час початку'), default=timezone.now)
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

    arbiters = models.ManyToManyField(Player, through='ArbiterTournamentMembership', related_name='tournament_arbiters')
    teams = models.ManyToManyField(Team, through='TeamTournamentMembership')
    notes = models.TextField(_('Нотатки'), blank=True, null=True)

    def __str__(self):
        return self.get_name()

    def get_name(self):
        return self.name

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
    extra = 1

    class Meta:
        verbose_name = 'Арбітри турніру'
        verbose_name_plural = 'Арбітри турніру'

# Classes for admin
class TeamsTournamentMembershipInline(admin.TabularInline):
    model = TeamTournamentMembership
    extra = 1

    class Meta:
        verbose_name = 'Команди турніру'
        verbose_name_plural = 'Команди турніру'

class ArbiterTeamTournamentAdminInline(admin.ModelAdmin):
    inlines = (ArbiterTournamentMembershipInline,TeamsTournamentMembershipInline,)