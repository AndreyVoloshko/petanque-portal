from django.db import models
from django_countries.fields import CountryField
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import admin
from .storage import AvatarsStorage
from django.utils.translation import ugettext_lazy as _

# Cities
class City (models.Model):
    name            = models.CharField(_('name'), max_length=150)
    country         = CountryField(blank_label='(select country)')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Мiсто'
        verbose_name_plural = 'Мiста'

# Clubs
class Club (models.Model):
    name            = models.CharField(_('name'), max_length=150)
    logo            = models.ImageField(_('avatar'), blank=True, null=True, storage=AvatarsStorage())
    short_name      = models.CharField(_('short_name'), max_length=50)
    date_registered = models.DateTimeField(_('date_registered'), default=timezone.now)
    date_created    = models.DateTimeField(_('date_created'), default=timezone.now)
    address         = models.CharField(_('address'), max_length=500)
    city            = models.ForeignKey('City')
    president       = models.ForeignKey('Player')
    facebook        = models.CharField(_('facebook'), max_length=500, blank=True, null=True)
    twitter         = models.CharField(_('twitter'), max_length=500, blank=True, null=True)
    instagram       = models.CharField(_('instagram'), max_length=500, blank=True, null=True)
    website         = models.CharField(_('website'), max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Клуб'
        verbose_name_plural = 'Клуби'

# Players
class Player(models.Model):
    GENDER_CHOICES = (
        ('M', 'Чоловiк'),
        ('F', 'Жiнка'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    avatar          = models.ImageField(_('avatar'), blank=True, null=True, storage=AvatarsStorage())
    name            = models.CharField(_('name'), max_length=100)
    surname         = models.CharField(_('surname'), max_length=100)
    birth_date      = models.DateField(_('birth_date'))
    current_club    = models.ForeignKey('Club', models.SET_NULL, blank=True, null=True)
    country         = CountryField(blank_label=_('(select country)'))
    licence_number  = models.CharField(_('licence_number'), max_length=50, blank=True, null=True)
    gender          = models.CharField(_('gender'), max_length=1, choices=GENDER_CHOICES)

    facebook        = models.CharField(_('facebook'), max_length=500, blank=True, null=True)
    twitter         = models.CharField(_('twitter'), max_length=500, blank=True, null=True)
    instagram       = models.CharField(_('instagram'), max_length=500, blank=True, null=True)
    website         = models.CharField(_('website'), max_length=500, blank=True, null=True)

    local_tournament_points     = models.FloatField(_('local_tournament_points'), default=0)
    foreign_tournament_points   = models.FloatField(_('foreign_tournament_points'), default=0)
    b_tournament_points         = models.FloatField(_('b_tournament_points'), default=0)

    def __str__(self):
        return self.get_name()

    def get_name(self):
        return self.name + " " + self.surname.upper()

    class Meta:
        verbose_name = 'Гравець'
        verbose_name_plural = 'Гравці'


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


# Tournaments
class Tournament(models.Model):
    TYPE_CHOICES = (
        ('open', 'Вiдктитий'),
        ('fpu', 'ФПУ'),
        ('away', 'Закордонний'),
    )

    FORMAT_CHOICES = (
        ('swiss', 'Швейцарська система'),
        ('swissko', 'Швейцарська система + На виліт'),
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