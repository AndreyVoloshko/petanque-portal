from django import forms
from django.urls import reverse
from federation.models.tournament import Tournament
from federation.models.player import Player
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div
from django.utils.translation import gettext_lazy as _

PLAYER_SEARCH_MINIMUM_INPUT_LENGTH = 2


class RegistrationTeamForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop('tournament')
        self.verified_player_ids = []
        self.verified_coach_id = None

        super(RegistrationTeamForm, self).__init__(*args, **kwargs)

        for i in range(self.tournament.get_max_players_per_team(), 0, -1):
            field_name = 'players[%d]' % i
            label = _("Player %(number)s") % {'number': i}
            if i == 1:
                label = _("%(player)s (Captain)") % {'player': label}
            elif i > self.tournament.number_of_players_in_team_min:
                label = _("%(player)s (Reserve)") % {'player': label}

            field = forms.CharField(
                widget=forms.Select(
                    attrs={
                        'class': 'player-autocomplete',
                        'data-player_index': i,
                        'data-minimum-input-length': PLAYER_SEARCH_MINIMUM_INPUT_LENGTH,
                        'data-placeholder': _("Search athlete by first or last name"),
                    },
                ),
                label=label,
                required=(i <= self.tournament.number_of_players_in_team_min),
            )
            selected_player_id = None
            if self.is_bound:
                selected_player_id = self.data.get(field_name)
            elif self.initial.get(field_name):
                selected_player_id = self.initial.get(field_name)

            if selected_player_id:
                try:
                    selected_player = Player.objects.get(pk=selected_player_id)
                    field.widget.choices = [(selected_player.pk, selected_player.get_name())]
                except Player.DoesNotExist:
                    field.widget.choices = [(selected_player_id, selected_player_id)]

            self.fields[field_name] = field

        self.fields['coach'] = forms.CharField(
            widget=forms.Select(
                attrs={
                    'class': 'player-autocomplete',
                    'data-minimum-input-length': PLAYER_SEARCH_MINIMUM_INPUT_LENGTH,
                    'data-placeholder': _("Search coach by first or last name"),
                },
            ),
            label=_("Coach"),
            required=False,
        )
        selected_coach_id = None
        if self.is_bound:
            selected_coach_id = self.data.get('coach')
        elif self.initial.get('coach'):
            selected_coach_id = self.initial.get('coach')

        if selected_coach_id:
            try:
                selected_coach = Player.objects.get(pk=selected_coach_id)
                self.fields['coach'].widget.choices = [(selected_coach.pk, selected_coach.get_name())]
            except Player.DoesNotExist:
                self.fields['coach'].widget.choices = [(selected_coach_id, selected_coach_id)]

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('register_team', args=[self.tournament.pk])

        self.helper.layout = Layout(
            Div(css_class="clear"),
            Div(
                Submit('submit', _("Register team"), css_class='btn btn-success'),
                css_class="col-lg-12 text-center mb-3"
            ),
            Div(css_class="clear")
        )

        for i in range(self.tournament.get_max_players_per_team(), 0, -1):
            self.helper.layout.insert(1, Div(
                'players[%d]' % i,
                css_class="col-lg-12"
            ))

    def ordered_player_fields(self):
        return [
            self['players[%d]' % i]
            for i in range(1, self.tournament.get_max_players_per_team() + 1)
        ]

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
            try:
                player = Player.objects.get(pk=player_id)
            except Player.DoesNotExist:
                self.add_error(None, _('Player with number %(player_id)s does not exist') % {'player_id': player_id})
                return False

            user_team = self.tournament.get_team_which_contains_player(player)
            if user_team:
                self.add_error(
                    None,
                    _('Player %(player)s is already registered for the tournament in team %(team)s') % {
                        'player': player.get_name(),
                        'team': user_team.team.get_short_name(),
                    }
                )
                return False

            self.verified_player_ids.append(player.pk)

        self.verified_coach_id = None
        coach_id = self.cleaned_data.get('coach')
        if coach_id:
            try:
                coach = Player.objects.get(pk=coach_id)
            except Player.DoesNotExist:
                self.add_error(None, _('Coach with number %(coach_id)s does not exist') % {'coach_id': coach_id})
                return False
            self.verified_coach_id = coach.pk

        return True
