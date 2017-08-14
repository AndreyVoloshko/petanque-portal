from django.db import models
from django.utils import timezone
from federation.storage import AvatarsStorage
from django.utils.translation import ugettext_lazy as _


# Clubs
class Club (models.Model):
    name = models.CharField(_('name'), max_length=150)
    logo  = models.ImageField(_('avatar'), blank=True, null=True, storage=AvatarsStorage())
    short_name = models.CharField(_('short_name'), max_length=50)
    date_registered = models.DateTimeField(_('date_registered'), default=timezone.now)
    date_created = models.DateTimeField(_('date_created'), default=timezone.now)
    address = models.CharField(_('address'), max_length=500)
    city = models.ForeignKey('City')
    president = models.ForeignKey('Player')
    facebook = models.CharField(_('facebook'), max_length=500, blank=True, null=True)
    twitter = models.CharField(_('twitter'), max_length=500, blank=True, null=True)
    instagram = models.CharField(_('instagram'), max_length=500, blank=True, null=True)
    website = models.CharField(_('website'), max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Клуб'
        verbose_name_plural = 'Клуби'
