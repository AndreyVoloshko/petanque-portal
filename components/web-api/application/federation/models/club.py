from django.db import models
from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from federation.admin_mixins import RestrictedRelatedWidgetAdminMixin
from federation.audit_admin import RevertibleAuditAdminMixin
from federation.models.player import Player
from federation.storage import MediaStorage
from federation.validators import IMAGE_UPLOAD_VALIDATORS


# Clubs
class Club (models.Model):
    name = models.CharField(_('Full name'), max_length=150)
    logo = models.ImageField(
        _('avatar'), blank=True, null=True, storage=MediaStorage(),
        validators=IMAGE_UPLOAD_VALIDATORS,
    )
    short_name = models.CharField(_('Short name'), max_length=50)
    is_active = models.BooleanField(_('Active'), default=True)
    date_registered = models.DateTimeField(_('Registration date'), default=timezone.now)
    date_created = models.DateTimeField(_('Creation date'), default=timezone.now)
    address = models.CharField(_('Address'), max_length=500)
    city = models.ForeignKey('City', verbose_name="Мiсто", on_delete=models.SET_NULL, null=True)
    president = models.ForeignKey('Player', verbose_name="Президент", on_delete=models.SET_NULL, null=True)
    facebook = models.CharField(_('facebook'), max_length=500, blank=True, null=True)
    twitter = models.CharField(_('twitter'), max_length=500, blank=True, null=True)
    instagram = models.CharField(_('instagram'), max_length=500, blank=True, null=True)
    website = models.CharField(_('website'), max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        """Clubs must be hidden (is_active=False), never hard-deleted."""
        raise PermissionError('Clubs cannot be deleted. Set is_active=False to hide the club instead.')

    class Meta:
        verbose_name = 'Клуб'
        verbose_name_plural = 'Клуби'


class ClubPlayerInline(admin.TabularInline):
    """Read-only roster so admins can see a club's players without a footgun.

    Adding/removing players still happens on the Player admin: an editable
    reverse-FK inline would let the "delete row" checkbox delete the Player
    itself (Django deletes the child object, it doesn't just clear the FK).
    """

    model = Player
    fk_name = 'current_club'
    verbose_name = 'Гравець клубу'
    verbose_name_plural = 'Гравці клубу'
    fields = ('player_link', 'licence_number', 'is_licence_active', 'current_rating')
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def player_link(self, obj):
        url = reverse('admin:federation_player_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.get_name())
    player_link.short_description = 'Гравець'


class ClubAdmin(RestrictedRelatedWidgetAdminMixin, RevertibleAuditAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'city', 'president', 'logo', 'is_active')
    list_editable = ('is_active',)
    search_fields = ['name', 'city__name', 'president__name', 'president__surname', 'city__id', 'president__id', ]
    list_per_page = 25
    autocomplete_fields = ['city', 'president']
    inlines = [ClubPlayerInline]

    def has_delete_permission(self, request, obj=None):
        return False

class CityAdmin(admin.ModelAdmin):
    search_fields = ['name']

