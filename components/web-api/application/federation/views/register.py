from django.shortcuts import render
from django.shortcuts import get_object_or_404
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from federation.forms.registration_team_form import RegistrationTeamForm


def register_team(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    is_registration_opened = tournament.is_registration_opened()

    team_registration_form = RegistrationTeamForm(tournament=tournament)

    return render(request, 'register/team.html', {
        'tournament': tournament,
        'is_registration_opened': is_registration_opened,
        'team_registration_form': team_registration_form,
        'page_title': "Реєстрація команди",
    })