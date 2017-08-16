from django.db import models
from django_countries.fields import CountryField
from django.contrib.auth.models import User
from federation.storage import AvatarsStorage
from django.utils.translation import ugettext_lazy as _


# Players
class Player(models.Model):
    GENDER_CHOICES = (
        ('M', 'Чоловiк'),
        ('F', 'Жiнка'),
    )

    ARBITER_CATEGORY = (
        ('club', 'Клубний'),
        ('regional', 'Регіональний'),
        ('national', 'Національний'),
        ('euro', 'Європейський'),
        ('fipjp', 'Міжнародний'),
    )

    POSITIONS = (
        ('point', 'Поінтер'),
        ('middle', 'Мідл'),
        ('shooter', 'Шутер'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    avatar = models.ImageField(_('avatar'), blank=True, null=True, storage=AvatarsStorage())
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

    local_tournament_points = models.FloatField(_('local_tournament_points'), default=0)
    foreign_tournament_points = models.FloatField(_('foreign_tournament_points'), default=0)
    b_tournament_points = models.FloatField(_('b_tournament_points'), default=0)

    arbiter_level = models.CharField(_('Рівень арбітражу'), max_length=10, choices=ARBITER_CATEGORY, blank=True, null=True)

    def __str__(self):
        return self.get_name()

    def get_name(self):
        return self.name + " " + self.surname.upper()

    class Meta:
        verbose_name = 'Гравець'
        verbose_name_plural = 'Гравці'
