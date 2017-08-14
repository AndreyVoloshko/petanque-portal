from django.db import models
from django_countries.fields import CountryField
from django.utils.translation import ugettext_lazy as _


# Cities
class City (models.Model):
    name = models.CharField(_('name'), max_length=150)
    country = CountryField(blank_label='(select country)')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Мiсто'
        verbose_name_plural = 'Мiста'
