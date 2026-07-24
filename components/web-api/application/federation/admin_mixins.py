from django.contrib.admin.widgets import RelatedFieldWidgetWrapper


class RestrictedRelatedWidgetAdminMixin:
    """Keep only the change and view shortcuts on related-object widgets.

    The add (+) and delete (x) icons Django puts next to a foreign-key
    dropdown act on the *related* object, not the field being edited:
    delete permanently removes that object (e.g. deleting a club's
    president instead of just clearing the field), and add can silently
    create a near-duplicate record. Managing those objects belongs on
    their own admin page, not as a side effect of editing something else.
    """

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # Django wraps the widget in RelatedFieldWidgetWrapper here (after
        # calling formfield_for_foreignkey/formfield_for_manytomany), so the
        # wrapper only exists once this method returns it.
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        widget = getattr(formfield, 'widget', None)
        if isinstance(widget, RelatedFieldWidgetWrapper):
            widget.can_add_related = False
            widget.can_delete_related = False
        return formfield
