from datetime import timedelta
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class EmailConfirmation(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_confirmation')
    email = models.EmailField(_('Email address'))
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(_('Creation date'), auto_now_add=True)
    confirmed = models.BooleanField(_('Confirmed'), default=False)
    confirmed_at = models.DateTimeField(_('Confirmation date'), null=True, blank=True)

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(hours=24)

    def __str__(self):
        return '{}: {}'.format(self.user.username, self.email)

    class Meta:
        verbose_name = 'Підтвердження email'
        verbose_name_plural = 'Підтвердження email'
