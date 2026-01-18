from django.db import models
from federation.storage import MediaStorage
from django.utils.translation import gettext_lazy as _


# Document Categories
class DocumentCategory(models.Model):
    code = models.CharField(_('Код'), max_length=100, unique=True, help_text=_('Унікальний код категорії (наприклад: fpu, tournaments)'))
    name = models.CharField(_('Назва'), max_length=200)
    order = models.IntegerField(_('Порядок'), default=0, help_text=_('Порядок відображення в списку'))
    is_active = models.BooleanField(_('Активна'), default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категорія документів'
        verbose_name_plural = 'Категорії документів'
        ordering = ['order', 'name']


# Documents
class Document (models.Model):
    name = models.CharField(_('Назва'), max_length=150)
    notes = models.TextField(_('Нотатки'), blank=True, null=True)
    file = models.FileField(_('Файл'), blank=False, null=False, storage=MediaStorage())
    category = models.ForeignKey(DocumentCategory, on_delete=models.PROTECT, verbose_name=_('Категорія'), related_name='documents')
    is_active = models.BooleanField(_('Доступний'), default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документи'
