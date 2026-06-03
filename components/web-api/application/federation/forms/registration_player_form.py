from django import forms
from django.urls import reverse
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.safestring import mark_safe
from federation.models.player import Player
from django.utils.translation import gettext_lazy as _
from federation.utils.countries import get_ordered_country_choices
from federation.utils.autocaptcha import validate_autocaptcha


class RegistrationPlayerForm(forms.Form):
    form_control_class = 'registration-form-control'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)

        super(RegistrationPlayerForm, self).__init__(*args, **kwargs)
        selected_country = self.data.get('country') if self.data else self.initial.get('country')
        patronymic_style = '' if selected_country == 'UA' else 'display: none;'

        self.fields['name'] = forms.CharField(
            widget=forms.TextInput(attrs={'class': self.form_control_class, 'autocomplete': 'given-name'}),
            label=_("First name"),
            required=True,
        )

        self.fields['surname'] = forms.CharField(
            widget=forms.TextInput(attrs={'class': self.form_control_class, 'autocomplete': 'family-name'}),
            label=_("Last name"),
            required=True,
        )

        self.fields['patronymic'] = forms.CharField(
            widget=forms.TextInput(attrs={'class': self.form_control_class, 'autocomplete': 'additional-name'}),
            label=_("Patronymic"),
            help_text=_("Optional. Required for tournament result protocols."),
            required=False,
        )

        self.fields['birth_date'] = forms.DateField(
            input_formats=['%d.%m.%Y', '%Y-%m-%d'],
            widget=forms.DateInput(
                format='%d.%m.%Y',
                attrs={
                    'class': self.form_control_class,
                    'placeholder': 'dd.mm.yyyy',
                    'inputmode': 'numeric',
                },
            ),
            label=_("Date of birth"),
            required=True,
        )

        self.fields['country'] = forms.ChoiceField(
            choices=get_ordered_country_choices(),
            widget=forms.Select(attrs={'class': self.form_control_class}),
            label=_("Country"),
            required=True
        )

        self.fields['gender'] = forms.CharField(
            widget=forms.Select(choices=Player.GENDER_CHOICES, attrs={'class': self.form_control_class}),
            label=_("Gender"),
            required=True,
        )

        self.fields['licence_number'] = forms.CharField(
            widget=forms.TextInput(attrs={'class': self.form_control_class}),
            label=_("License number"),
            help_text=_("Only for players who already have a license issued by the federation."),
            required=False,
        )

        self.fields['email'] = forms.EmailField(
            widget=forms.EmailInput(attrs={'class': self.form_control_class, 'autocomplete': 'email'}),
            label=_("Email"),
            required=False,
        )

        self.fields['password'] = forms.CharField(
            widget=forms.PasswordInput(attrs={'class': self.form_control_class, 'autocomplete': 'new-password'}),
            label=_("Password"),
            required=False,
        )

        self.fields['password_confirm'] = forms.CharField(
            widget=forms.PasswordInput(attrs={'class': self.form_control_class, 'autocomplete': 'new-password'}),
            label=_("Confirm password"),
            required=False,
        )

        self.fields['autocaptcha_token'] = forms.CharField(
            widget=forms.HiddenInput(),
            required=False,
        )

    def _get_remote_ip(self):
        if not self.request:
            return None

        forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        return self.request.META.get('REMOTE_ADDR')

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date and birth_date > timezone.localdate():
            raise ValidationError(_("Date of birth cannot be in the future"))

        return birth_date

    def clean(self):
        cleaned_data = super(RegistrationPlayerForm, self).clean()

        name = cleaned_data.get('name')
        surname = cleaned_data.get('surname')
        if name and surname:
            existing_player = Player.get_by_name_and_surname(name, surname)
            if existing_player:
                player_url = reverse('player', kwargs={'id': existing_player.pk})
                self.add_error(None, mark_safe(
                    _('Player <a target="_blank" href="%(url)s">%(name)s %(surname)s</a> is already registered') % {
                        'url': player_url,
                        'name': name,
                        'surname': surname,
                    }
                ))

        country = cleaned_data.get('country')
        email = cleaned_data.get('email') or ''
        password = cleaned_data.get('password') or ''
        password_confirm = cleaned_data.get('password_confirm') or ''
        if country != 'UA':
            cleaned_data['patronymic'] = ''
            cleaned_data['email'] = ''
            cleaned_data['password'] = ''
            cleaned_data['password_confirm'] = ''
        else:
            if not email:
                cleaned_data['password'] = ''
                cleaned_data['password_confirm'] = ''
            elif User.objects.filter(email__iexact=email).exists():
                self.add_error('email', _('This email is already in use'))

            if email and not password:
                self.add_error('password', _('Password is required when email is provided'))

            if email and not password_confirm:
                self.add_error('password_confirm', _('Confirm password is required when password is provided'))

            if password and password_confirm and password != password_confirm:
                self.add_error('password_confirm', _('Passwords do not match'))

            if password:
                try:
                    password_validation.validate_password(password)
                except ValidationError as error:
                    self.add_error('password', error)

        if not self.errors:
            try:
                validate_autocaptcha(
                    cleaned_data.get('autocaptcha_token'),
                    remote_ip=self._get_remote_ip(),
                )
            except ValidationError as error:
                self.add_error(None, error)

        return cleaned_data
