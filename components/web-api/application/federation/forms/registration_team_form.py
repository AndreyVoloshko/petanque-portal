from django import forms
from django.urls import reverse
from federation.models.tournament import Tournament
from federation.models.player import Player
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML, Field
from captcha.fields import ReCaptchaField


class RegistrationTeamForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop('tournament')
        self.verified_player_ids = []

        super(RegistrationTeamForm, self).__init__(*args, **kwargs)

        for i in range(self.tournament.get_max_players_per_team(), 0, -1):
            extra_label = ""
            if i == 1:
                extra_label = " (Капітан)"
            elif i > self.tournament.number_of_players_in_team_min:
                extra_label = " (Резерв)"

            self.fields['players[%d]' % i] = forms.CharField(
                widget=forms.Select(attrs={'class': 'player-autocomplete', 'data-player_index': i}),
                label="Гравець " + str(i) + extra_label,
                required=(i <= self.tournament.number_of_players_in_team_min),
            )

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('register_team', args=[self.tournament.pk])

        self.fields['captcha'] = ReCaptchaField(
            label="Додаткова перевірка"
        )

        self.helper.layout = Layout(
            HTML('<hr class="clear" />'),
            HTML('<hr class="clear" />'),
            Div(
                'captcha',
                css_class="col-md-12"
            ),
            Div(
                Submit('submit', 'Зареєструвати команду', css_class='btn btn-success'),
                css_class="col-md-12 text-center form-group"
            ),
            Div(css_class="clear")
        )

        for i in range(self.tournament.get_max_players_per_team(), 0, -1):
            self.helper.layout.insert(1, Div(
                'players[%d]' % i,
                css_class="col-md-12"
            ))

    def is_valid(self):
        # run the parent validation first
        valid = super(RegistrationTeamForm, self).is_valid()

        # we're done now if not valid
        if not valid:
            return valid

        # get player ids as list
        player_ids = []
        for i in range(self.tournament.get_max_players_per_team(), 0, -1):
            if self.cleaned_data['players[%d]' % i]:
                player_ids.append(self.cleaned_data['players[%d]' % i])

        # check players
        self.verified_player_ids = []
        for player_id in player_ids:
            player = Player.objects.get(pk=player_id)
            if not player:
                self._errors['no_player'] = 'Гравець з номером '+player_id+' не існує'
                return False

            user_team = self.tournament.get_team_which_contains_player(player)
            if user_team:
                self._errors['player_is_already_registered'] = 'Гравець '+player.get_name()+' вже зареєстрований турнір у команді '+user_team.team.get_short_name()
                return False

            self.verified_player_ids.append(player.pk)

        return True
