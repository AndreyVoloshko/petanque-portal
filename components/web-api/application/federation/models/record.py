from django.utils import timezone
from django.db import models
from django.utils.translation import gettext_lazy as _


# Cities
class Record (models.Model):
    name = models.CharField(_('name'), max_length=150)
    player = models.ForeignKey('Player', blank=True, verbose_name="Гравець", on_delete=models.SET_NULL, null=True)
    club = models.ForeignKey('Club', blank=True, verbose_name="Клуб", on_delete=models.SET_NULL, null=True)
    description = models.CharField(_('Значення'), max_length=100)
    date_created = models.DateTimeField(_('Дата'), blank=True, null=True)
    notes = models.TextField(_('Опис'), blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Рекорд'
        verbose_name_plural = 'Рекорди'
