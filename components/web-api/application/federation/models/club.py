from django.db import models
from django.contrib import admin
from django.utils import timezone
from federation.storage import MediaStorage
from django.utils.translation import ugettext_lazy as _


# Clubs
class Club (models.Model):
    name = models.CharField(_('Повна назва'), max_length=150)
    logo  = models.ImageField(_('avatar'), blank=True, null=True, storage=MediaStorage())
    short_name = models.CharField(_('Коротка назва'), max_length=50)
    date_registered = models.DateTimeField(_('Дата реєстрації'), default=timezone.now)
    date_created = models.DateTimeField(_('Дата створення'), default=timezone.now)
    address = models.CharField(_('Адреса'), max_length=500)
    city = models.ForeignKey('City', verbose_name="Мiсто")
    president = models.ForeignKey('Player', verbose_name="Президент")
    facebook = models.CharField(_('facebook'), max_length=500, blank=True, null=True)
    twitter = models.CharField(_('twitter'), max_length=500, blank=True, null=True)
    instagram = models.CharField(_('instagram'), max_length=500, blank=True, null=True)
    website = models.CharField(_('website'), max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Клуб'
        verbose_name_plural = 'Клуби'


class ClubAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'city', 'president', 'logo',)
    search_fields = ('name', 'city__name', 'president__name', 'president__surname' )
    list_per_page = 25

