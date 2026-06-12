from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import NoReverseMatch, path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from federation.audit import (
    extract_changed_field_values,
    format_model_change_fields,
    get_log_entry_object,
    get_log_entry_revert_reason,
    get_model_change_filter_choices,
    get_model_change_filter_lookup_terms,
    is_revert_change_message,
    revert_log_entry,
)
from .models.document import Document
from .models.player import Player
from .models.tournament import Tournament


AUDITED_MODELS = (Player, Document, Tournament)


class AuditContentTypeFilter(admin.SimpleListFilter):
    """Limit the journal to one of the explicitly audited models."""

    title = _('content type')
    parameter_name = 'content_type__id__exact'

    def lookups(self, request, model_admin):
        return tuple(
            (
                content_type.pk,
                content_type.model_class()._meta.verbose_name if content_type.model_class() else content_type.name,
            )
            for content_type in model_admin.get_audited_content_types()
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(content_type_id=self.value())
        return queryset


class AuditChangedFieldFilter(admin.SimpleListFilter):
    """Filter LogEntry JSON by stable fields and historical display labels."""

    title = _('changed field')
    parameter_name = 'changed_field'

    def get_selected_model(self, request):
        """Resolve the model that determines available changed-field choices."""
        selected_content_type = request.GET.get(AuditContentTypeFilter.parameter_name)
        if not selected_content_type:
            return Player

        try:
            content_type = ContentType.objects.get(pk=selected_content_type)
        except ContentType.DoesNotExist:
            return None

        return content_type.model_class()

    def lookups(self, request, model_admin):
        selected_model = self.get_selected_model(request)
        if selected_model not in AUDITED_MODELS:
            return ()

        return get_model_change_filter_choices(selected_model)

    def queryset(self, request, queryset):
        selected_model = self.get_selected_model(request)
        if selected_model not in AUDITED_MODELS:
            return queryset

        lookup_terms = get_model_change_filter_lookup_terms(selected_model, self.value())
        if not lookup_terms:
            return queryset

        query = Q(content_type=ContentType.objects.get_for_model(selected_model))
        lookup_query = Q()
        for lookup_term in lookup_terms:
            lookup_query |= Q(change_message__contains=lookup_term)

        return queryset.filter(query & lookup_query)


class AuditUserFilter(admin.SimpleListFilter):
    """List only users that own entries visible in the audit journal."""

    title = _('changed by')
    parameter_name = 'changed_by'

    def lookups(self, request, model_admin):
        user_ids = (
            model_admin.model.objects
            .filter(content_type__in=model_admin.get_audited_content_types())
            .exclude(user_id__isnull=True)
            .order_by()
            .values_list('user_id', flat=True)
            .distinct()
        )

        return (
            get_user_model().objects
            .filter(pk__in=user_ids)
            .order_by('username')
            .values_list('pk', 'username')
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_id=self.value())
        return queryset


class AuditActionFilter(admin.SimpleListFilter):
    """Filter journal entries without exposing LogEntry's technical field name."""

    title = _('journal action')
    parameter_name = 'action_flag'

    def lookups(self, request, model_admin):
        return model_admin.model._meta.get_field('action_flag').choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(action_flag=self.value())
        return queryset


class AuditActionTimeFilter(admin.DateFieldListFilter):
    """Use a journal-specific title for Django's date filter."""

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        self.title = _('journal action time')


class AuditLogAdmin(admin.ModelAdmin):
    """Read-only journal with guarded reverts for selected model changes."""

    change_form_template = 'admin/audit_log/change_form.html'
    date_hierarchy = 'action_time'
    list_display = (
        'action_time',
        'changed_by',
        'content_type_label',
        'content_object_link',
        'action_name',
        'changed_fields',
    )
    list_filter = (
        AuditContentTypeFilter,
        AuditChangedFieldFilter,
        AuditUserFilter,
        AuditActionFilter,
        ('action_time', AuditActionTimeFilter),
    )
    list_per_page = 50
    ordering = ('-action_time',)
    readonly_fields = (
        'action_time',
        'user',
        'content_type',
        'object_id',
        'content_object_link',
        'action_name',
        'changed_fields',
    )
    fields = readonly_fields
    search_fields = ('object_repr', 'object_id', 'user__username', 'change_message')

    def get_audited_content_types(self):
        """Return the content types intentionally exposed by this journal."""
        return ContentType.objects.get_for_models(*AUDITED_MODELS).values()

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('user', 'content_type')
            .filter(content_type__in=self.get_audited_content_types())
        )

    def get_urls(self):
        return [
            path(
                '<path:object_id>/revert/',
                self.admin_site.admin_view(self.revert_view),
                name='admin_logentry_revert',
            ),
        ] + super().get_urls()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changed_by(self, obj):
        return obj.user or '-'
    changed_by.admin_order_field = 'user'
    changed_by.short_description = _('Changed by')

    def content_type_label(self, obj):
        model = obj.content_type.model_class()
        return model._meta.verbose_name if model else obj.content_type.name
    content_type_label.admin_order_field = 'content_type'
    content_type_label.short_description = _('Content type')

    def content_object_link(self, obj):
        model = obj.content_type.model_class()
        if not model or not obj.object_id:
            return obj.object_repr

        if not model.objects.filter(pk=obj.object_id).exists():
            return obj.object_repr

        try:
            url = reverse('admin:{}_{}_change'.format(model._meta.app_label, model._meta.model_name), args=[obj.object_id])
        except NoReverseMatch:
            return obj.object_repr

        return format_html('<a href="{}">{}</a>', url, obj.object_repr)
    content_object_link.short_description = _('Object')

    def action_name(self, obj):
        if is_revert_change_message(obj.change_message):
            return _('Reverted')
        return obj.get_action_flag_display()
    action_name.admin_order_field = 'action_flag'
    action_name.short_description = _('Action')

    def changed_fields(self, obj):
        model = obj.content_type.model_class()
        formatted_fields = format_model_change_fields(model, obj.change_message) if model else ''
        return formatted_fields or obj.get_change_message()
    changed_fields.short_description = _('Changed fields')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj is not None:
            extra_context.update(self.get_change_view_context(request, obj))
        return super().change_view(request, object_id, form_url=form_url, extra_context=extra_context)

    def get_change_view_context(self, request, obj):
        revert_reason = self.get_revert_reason(request, obj)
        return {
            'can_revert_change': not revert_reason,
            'revert_reason': revert_reason,
            'revert_url': reverse('admin:admin_logentry_revert', args=[obj.pk]),
            'subtitle': self.get_entry_summary(obj),
            'audit_breadcrumb_title': self.get_entry_summary(obj),
        }

    def get_entry_summary(self, obj):
        changed_fields = self.changed_fields(obj)
        if is_revert_change_message(obj.change_message):
            return _('Reverted "%(object)s" - %(changes)s') % {
                'object': obj.object_repr,
                'changes': changed_fields or obj.get_change_message(),
            }

        return str(obj)

    def get_revert_reason(self, request, obj):
        """Return the first data-integrity or permission reason blocking revert."""
        revert_reason = str(get_log_entry_revert_reason(obj) or '')
        if revert_reason:
            return revert_reason

        if not self.has_target_change_permission(request, obj):
            return _('You do not have permission to revert this change.')

        return ''

    def has_target_change_permission(self, request, obj):
        """Delegate revert authorization to the target model's admin."""
        target_model = obj.content_type.model_class()
        target_obj = get_log_entry_object(obj)
        if not target_model or target_obj is None:
            return False

        model_admin = self.admin_site._registry.get(target_model)
        if model_admin is None:
            return False

        if not model_admin.has_change_permission(request, target_obj):
            return False

        field_values = extract_changed_field_values(obj.change_message)
        if target_model == Player and 'email' in field_values:
            user_admin = self.admin_site._registry.get(get_user_model())
            return bool(user_admin and user_admin.has_change_permission(request, target_obj.user))

        return True

    def revert_view(self, request, object_id):
        """Handle the POST-only revert action from a journal detail page."""
        if request.method != 'POST':
            raise PermissionDenied

        log_entry = self.get_object(request, object_id)
        if log_entry is None:
            raise PermissionDenied

        revert_reason = self.get_revert_reason(request, log_entry)
        if revert_reason:
            messages.error(request, revert_reason)
            return HttpResponseRedirect(reverse('admin:admin_logentry_change', args=[log_entry.pk]))

        try:
            new_log_entry = revert_log_entry(log_entry, request.user)
        except ValueError as error:
            # The locked revalidation can reject a change made after the
            # page-level permission and staleness checks completed.
            messages.error(request, str(error))
            return HttpResponseRedirect(reverse('admin:admin_logentry_change', args=[log_entry.pk]))

        if new_log_entry:
            messages.success(
                request,
                format_html(
                    '{} <a href="{}">{}</a>.',
                    _('Change reverted.'),
                    reverse('admin:admin_logentry_change', args=[new_log_entry.pk]),
                    _('Open revert log entry'),
                ),
            )
        else:
            messages.success(request, _('Change reverted.'))

        return HttpResponseRedirect(reverse('admin:admin_logentry_change', args=[log_entry.pk]))
