from django.db import models
from django_countries.fields import CountryField
from django.utils import timezone
from django.contrib.auth.models import User
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
    licence_number  = models.CharField(_('licence_number'), max_length=50)
    gender          = models.CharField(_('gender'), max_length=1, choices=GENDER_CHOICES)

    facebook        = models.CharField(_('facebook'), max_length=500, blank=True, null=True)
    twitter         = models.CharField(_('twitter'), max_length=500, blank=True, null=True)
    instagram       = models.CharField(_('instagram'), max_length=500, blank=True, null=True)
    website         = models.CharField(_('website'), max_length=500, blank=True, null=True)

    local_tournament_points     = models.FloatField(_('local_tournament_points'), default=0)
    foreign_tournament_points   = models.FloatField(_('foreign_tournament_points'), default=0)
    b_tournament_points         = models.FloatField(_('b_tournament_points'), default=0)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Гравець'
        verbose_name_plural = 'Гравці'