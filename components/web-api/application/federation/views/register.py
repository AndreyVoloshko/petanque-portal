from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from federation.forms.registration_team_form import RegistrationTeamForm
from federation.models.team import Team
from django.contrib import messages


def register_team(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    is_registration_opened = tournament.is_registration_opened()

    team_registration_form = RegistrationTeamForm(tournament=tournament)

    if request.method == "POST":
        team_registration_form = RegistrationTeamForm(request.POST, tournament=tournament)
        if team_registration_form.is_valid():
            team = Team.get_or_create_for_players(player_ids=team_registration_form.verified_player_ids)
            tournament.add_team(team)
            tournament.recalculate_power_on_registration()
            messages.success(request, 'Команду зареєстровано.', extra_tags='success')
            return redirect('tournament', id=tournament.pk)
        else:
            for error_message in team_registration_form.errors:
                messages.error(request, team_registration_form.errors[error_message], extra_tags='danger')

    return render(request, 'register/team.html', {
        'tournament': tournament,
        'is_registration_opened': is_registration_opened,
        'team_registration_form': team_registration_form,
        'page_title': "Реєстрація команди",
    })