import os

from django.db import models
from django.utils import timezone
from federation.storage import MediaStorage
from django.utils.translation import gettext_lazy as _


# Document Categories
class DocumentCategory(models.Model):
    code = models.CharField(_('Code'), max_length=100, unique=True, help_text=_('Unique category code (for example: fpu, tournaments)'))
    name = models.CharField(_('Name'), max_length=200)
    order = models.IntegerField(_('Order'), default=0, help_text=_('Display order in the list'))
    is_active = models.BooleanField(_('Active'), default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категорія документів'
        verbose_name_plural = 'Категорії документів'
        ordering = ['order', 'name']


# Documents
class Document(models.Model):
    name = models.CharField(_('Name'), max_length=150)
    notes = models.TextField(_('Notes'), blank=True, null=True)
    file = models.FileField(_('File'), blank=False, null=False, storage=MediaStorage())
    category = models.ForeignKey(DocumentCategory, on_delete=models.PROTECT, verbose_name=_('Category'), related_name='documents')
    is_active = models.BooleanField(_('Available'), default=True)
    document_date = models.DateField(_('Document date'), blank=True, null=True, help_text=_('Publication or issue date of the document'))
    created_at = models.DateTimeField(_('Created at'), default=timezone.now)
    download_count = models.PositiveIntegerField(_('Download count'), default=0)

    def __str__(self):
        return self.name

    @property
    def file_extension(self):
        if self.file and self.file.name:
            _, ext = os.path.splitext(self.file.name)
            return ext.lstrip('.').lower()
        return ''

    @property
    def effective_date(self):
        return self.display_date

    @property
    def display_date(self):
        return self.document_date or (self.created_at.date() if self.created_at else None)

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документи'
        ordering = ['-document_date', '-created_at']
