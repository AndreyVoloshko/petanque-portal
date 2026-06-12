from federation.audit import capture_model_change_values, replace_changed_fields_in_message


class RevertibleAuditAdminMixin:
    """Enrich Django admin change logs with values required for safe revert."""

    audit_request_attr = '_audit_field_values'

    def get_audit_before_instance(self, obj):
        """Load the persisted object before Django admin saves form changes."""
        return self.model.objects.get(pk=obj.pk)

    def get_audit_changed_fields(self, form):
        """Return candidate fields changed by the Django admin form."""
        return getattr(form, 'changed_data', [])

    def capture_audit_field_values(self, before_instance, after_instance, changed_fields):
        """Capture auditable values for candidate fields changed by the form."""
        return capture_model_change_values(before_instance, after_instance, changed_fields)

    def save_model(self, request, obj, form, change):
        before_instance = None
        if change and obj.pk:
            before_instance = self.get_audit_before_instance(obj)

        super().save_model(request, obj, form, change)

        if before_instance is not None:
            # Django builds the LogEntry message after save_model(), so retain
            # the pre-save comparison on this request for that later hook.
            setattr(
                request,
                self.audit_request_attr,
                self.capture_audit_field_values(before_instance, obj, self.get_audit_changed_fields(form)),
            )

    def construct_change_message(self, request, form, formsets, add=False):
        """Attach captured values without discarding Django inline messages."""
        change_message = super().construct_change_message(request, form, formsets, add)
        if add or not isinstance(change_message, list):
            return change_message

        return replace_changed_fields_in_message(
            change_message,
            self.get_audit_changed_fields(form),
            field_values=getattr(request, self.audit_request_attr, None),
        )

    def log_change(self, request, obj, message):
        """Skip empty entries when every changed field is intentionally ignored."""
        if not message:
            return None

        return super().log_change(request, obj, message)
