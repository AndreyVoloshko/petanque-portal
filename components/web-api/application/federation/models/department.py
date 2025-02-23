from django.db import models
from django.db.models import Count
from django.utils import timezone
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from federation.models.player import Player


# Department
class Department(models.Model):
    default_name = "-"

    name            = models.CharField(_('Назва'), max_length=1000, blank=False, null=False)
    order           = models.IntegerField(_('Порядок у меню'), default=0)
    players         = models.ManyToManyField(Player, through='PlayerDepartmentMembership', verbose_name="Гравці")
    date_created    = models.DateTimeField(_('Дата створення'), default=timezone.now)
    notes           = models.TextField(_('Нотатки'), blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Підрозділ ФПУ'
        verbose_name_plural = 'Підрозділи ФПУ'


# Players to Teams relation
class PlayerDepartmentMembership(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, verbose_name="Гравцi", null=True)
    team = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name="Підрозділи ФПУ", null=True)
    role = models.CharField(_('Роль'), max_length=1000, blank=False, null=False)

    class Meta:
        verbose_name = 'Належнiсть до підрозділу'
        verbose_name_plural = 'Належнiсть до підрозділу'


# Classes for admin
class PlayerDepartmentMembershipInline(admin.TabularInline):
    model = PlayerDepartmentMembership
    extra = 1

    class Meta:
        verbose_name = 'Належнiсть до підрозділу'
        verbose_name_plural = 'Належнiсть до підрозділу'


class PlayerDepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'order', 'date_created', 'notes',)
    search_fields = ('name', 'date_created', 'notes', 'players__name', 'players__surname', )
    list_per_page = 25
    inlines = (PlayerDepartmentMembershipInline,)


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    search_fields = ('name', 'players__name', 'players__surname', )
    list_per_page = 25
    inlines = (PlayerDepartmentMembershipInline,)