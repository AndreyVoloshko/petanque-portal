from django.db import models
from federation.storage import MediaStorage
from django.utils.translation import gettext_lazy as _


# Documents
class Document (models.Model):
    CATEGORIES = (
        ('fpu', 'Свідоцтва та установчі документи ФПУ'),
        ('tournaments', 'Положення та правила проведення змагань'),
        ('international', 'Документи CEP, FIPJP, CMSB'),
        ('forms', 'Форми документів для організаторів змагань та спортсменів'),
        ('rules', 'Правила'),
        ('regulations', 'Регламентні документи'),
        ('tournament_regulations', 'Регламенти турнірів'),
        ('for_print', 'Документи до друку'),
        ('official', 'Свідоцтва та офіційні документи'),
        ('other', 'Інше'),
    )

    name = models.CharField(_('Назва'), max_length=150)
    notes = models.TextField(_('Нотатки'), blank=True, null=True)
    file = models.FileField(_('Файл'), blank=False, null=False, storage=MediaStorage())
    category = models.CharField(_('Категорія'), max_length=100, choices=CATEGORIES)
    is_active = models.BooleanField(_('Доступний'), default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документи'
