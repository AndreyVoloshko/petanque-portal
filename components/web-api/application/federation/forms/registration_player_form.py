from django import forms
from django.urls import reverse
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from federation.models.player import Player
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div
from django.utils.translation import gettext_lazy as _
from federation.utils.countries import get_ordered_country_choices
from federation.utils.autocaptcha import validate_autocaptcha


class RegistrationPlayerForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)

        super(RegistrationPlayerForm, self).__init__(*args, **kwargs)
        selected_country = self.data.get('country') if self.data else self.initial.get('country')
        email_style = '' if selected_country == 'UA' else 'display: none;'
        patronymic_style = '' if selected_country == 'UA' else 'display: none;'

        self.fields['name'] = forms.CharField(
            widget=forms.TextInput(),
            label=_("First name"),
            required=True,
        )

        self.fields['surname'] = forms.CharField(
            widget=forms.TextInput(),
            label=_("Last name"),
            required=True,
        )

        self.fields['patronymic'] = forms.CharField(
            widget=forms.TextInput(),
            label=_("Patronymic"),
            help_text=_("Optional. Required for tournament result protocols."),
            required=False,
        )

        self.fields['birth_date'] = forms.CharField(
            widget=forms.DateInput(attrs={'class': 'dateinput'}),
            label=_("Date of birth"),
            required=True,
        )

        self.fields['country'] = forms.ChoiceField(
            choices=get_ordered_country_choices(),
            label=_("Country"),
            required=True
        )

        self.fields['email'] = forms.EmailField(
            widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
            label=_("Email address"),
            help_text=_("Optional. You can leave this field empty."),
            required=False,
        )

        self.fields['password'] = forms.CharField(
            widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
            label=_("Password"),
            min_length=8,
            required=True,
        )

        self.fields['password_confirm'] = forms.CharField(
            widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
            label=_("Confirm password"),
            required=True,
        )

        self.fields['gender'] = forms.CharField(
            widget=forms.Select(choices=Player.GENDER_CHOICES),
            label=_("Gender"),
            required=True,
        )

        self.fields['licence_number'] = forms.CharField(
            widget=forms.TextInput(),
            label=_("License number"),
            help_text=_("Only for players who already have a license issued by the federation."),
            required=False,
        )

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('register_player')
        self.helper.form_id = 'player-registration-form'

        self.fields['autocaptcha_token'] = forms.CharField(
            widget=forms.HiddenInput(),
            required=False,
        )

        self.helper.layout = Layout(
            Div(
                'name',
                css_class="col-lg-12 mb-3"
            ),
            Div(
                'surname',
                css_class="col-lg-12 mb-3"
            ),
            Div(
                'patronymic',
                css_id="patronymic-field-group",
                css_class="col-lg-12 mb-3",
                style=patronymic_style
            ),
            Div(
                'birth_date',
                css_class="col-lg-12 mb-3"
            ),
            Div(
                'country',
                css_class="col-lg-12 mb-3"
            ),
            Div(
                'email',
                css_id="email-field-group",
                css_class="col-lg-12 mb-3",
                style=email_style
            ),
            Div(
                'password',
                css_class="col-lg-12 mb-3"
            ),
            Div(
                'password_confirm',
                css_class="col-lg-12 mb-3"
            ),
            Div(
                'gender',
                css_class="col-lg-12 mb-3"
            ),
            Div(
                'licence_number',
                css_class="col-lg-12 mb-3"
            ),
            Div(
                'autocaptcha_token',
                css_class="d-none"
            ),
            Div(
                Submit('submit', _("Register player"), css_class='btn btn-success'),
                css_class="col-lg-12 text-center mb-3"
            ),
            Div(css_class="clear")
        )

    def _get_remote_ip(self):
        if not self.request:
            return None

        forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        return self.request.META.get('REMOTE_ADDR')

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

        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', _('Passwords do not match'))

        if password:
            try:
                password_validation.validate_password(password)
            except ValidationError as error:
                self.add_error('password', error)

        country = cleaned_data.get('country')
        email = cleaned_data.get('email')
        if country != 'UA':
            cleaned_data['email'] = ''
            cleaned_data['patronymic'] = ''
        elif email and User.objects.filter(email__iexact=email).exists():
            self.add_error('email', _('This email is already in use'))

        if not self.errors:
            try:
                validate_autocaptcha(
                    cleaned_data.get('autocaptcha_token'),
                    remote_ip=self._get_remote_ip(),
                )
            except ValidationError as error:
                self.add_error(None, error)

        return cleaned_data
