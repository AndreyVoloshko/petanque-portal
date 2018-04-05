from django import forms
from django.urls import reverse
from federation.models.tournament import Tournament
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML, Field


class RegistrationTeamForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop('tournament')

        super(RegistrationTeamForm, self).__init__(*args, **kwargs)

        for i in range(self.tournament.get_max_players_per_team(), 0, -1):
            extra_label = ""
            if i == 1:
                extra_label = " (Капітан)"
            elif i > self.tournament.number_of_players_in_team_min:
                extra_label = " (Резерв)"

            self.fields['player[%d]' % i] = forms.CharField(
                widget=forms.TextInput(attrs={'class': 'player-autocomplete'}),
                label="Гравець " + str(i) + extra_label,
                required=(i <= self.tournament.number_of_players_in_team_min)
            )

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('register_team', args=[self.tournament.pk])

        self.helper.layout = Layout(
            HTML('<hr class="clear" />'),
            HTML('<hr class="clear" />'),
            Div(
                Submit('submit', 'Зареєструвати команду', css_class='btn btn-success'),
                css_class="col-md-12 text-center form-group"
            ),
            Div(css_class="clear")
        )

        for i in range(self.tournament.get_max_players_per_team(), 0, -1):
            self.helper.layout.insert(1, Div(
                'player[%d]' % i,
                css_class="col-md-12"
            ))
