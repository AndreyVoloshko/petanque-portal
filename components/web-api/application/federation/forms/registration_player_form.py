from django import forms
from django.urls import reverse
from federation.models.player import Player
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML, Field
from captcha.fields import ReCaptchaField
from django_countries.fields import CountryField


class RegistrationPlayerForm(forms.Form):

    def __init__(self, *args, **kwargs):

        super(RegistrationPlayerForm, self).__init__(*args, **kwargs)

        self.fields['name'] = forms.CharField(
            widget=forms.TextInput(),
            label="Ім'я / Name",
            required=True,
        )

        self.fields['surname'] = forms.CharField(
            widget=forms.TextInput(),
            label="Прізвищє / Surname",
            required=True,
        )

        self.fields['birth_date'] = forms.CharField(
            widget=forms.DateInput(),
            label="Дата народження / Birth date",
            required=True,
        )

        self.fields['country'] = CountryField().formfield(
            label="Країна / Country",
            required=True
        )

        self.fields['gender'] = forms.CharField(
            widget=forms.Select(choices=Player.GENDER_CHOICES),
            label="Стать / Sex",
            required=True,
        )

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('register_player')

        #self.fields['captcha'] = ReCaptchaField(
        #    label="Додаткова перевірка"
        #)

        self.helper.layout = Layout(
            Div(
                'name',
                css_class="col-md-12 form-group"
            ),
            Div(
                'surname',
                css_class="col-md-12 form-group"
            ),
            Div(
                'birth_date',
                css_class="col-md-12 form-group"
            ),
            Div(
                'country',
                css_class="col-md-12 form-group"
            ),
            Div(
                'gender',
                css_class="col-md-12 form-group"
            ),
            HTML('<hr class="clear" />'),
            #Div(
            #    'captcha',
            #    css_class="col-md-12"
            #),
            Div(
                Submit('submit', 'Зареєструвати гравця', css_class='btn btn-success'),
                css_class="col-md-12 text-center form-group"
            ),
            Div(css_class="clear")
        )

    def is_valid(self):
        # run the parent validation first
        valid = super(RegistrationPlayerForm, self).is_valid()

        # we're done now if not valid
        if not valid:
            return valid

        # check if player is already registered by name and surname
        existing_player = Player.get_by_name_and_surname(self.cleaned_data['name'], self.cleaned_data['surname'])
        if existing_player:
            self._errors['no_player'] = 'Гравець <a target="_blank" href="' + reverse('player', kwargs={'id': existing_player.pk}) + '">' + self.cleaned_data['name'] + " " +self.cleaned_data['surname'] + "</a> вже зарєстрований"
            return False

        return True
