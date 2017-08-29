from django.db import models
from django.utils.translation import ugettext_lazy as _


# Cities
class Record (models.Model):
    name = models.CharField(_('name'), max_length=150)
    player = models.ForeignKey('Player', models.SET_NULL, blank=True, null=True, verbose_name="Гравець")
    club = models.ForeignKey('Club', models.SET_NULL, blank=True, null=True, verbose_name="Клуб")
    description = models.CharField(_('Опис'), max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Рекорд'
        verbose_name_plural = 'Рекорди'
