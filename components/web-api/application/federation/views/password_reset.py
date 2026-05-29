from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView
from django.utils.translation import gettext_lazy as _

from federation.models.email_confirmation import EmailConfirmation


class ConfirmedPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super(ConfirmedPasswordResetForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'email',
            'placeholder': _('your.email@example.com'),
        })
        self.fields['email'].label = _('Email address')

    def get_users(self, email):
        UserModel = get_user_model()
        active_users = UserModel._default_manager.filter(email__iexact=email, is_active=True)
        for user in active_users:
            if not user.has_usable_password():
                continue
            if self._email_is_confirmed_or_legacy(user, email):
                yield user

    def _email_is_confirmed_or_legacy(self, user, email):
        try:
            confirmation = user.email_confirmation
        except EmailConfirmation.DoesNotExist:
            return True
        return confirmation.confirmed


class CustomPasswordResetView(PasswordResetView):
    form_class = ConfirmedPasswordResetForm

    def form_valid(self, form):
        email = form.cleaned_data['email']
        if not list(form.get_users(email)):
            return self.render_to_response(self.get_context_data(
                form=form,
                email_not_found=True,
            ))
        return super(CustomPasswordResetView, self).form_valid(form)


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(StyledSetPasswordForm, self).__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password',
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password',
        })


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = StyledSetPasswordForm
