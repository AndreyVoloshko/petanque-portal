from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from federation.forms.registration_team_form import RegistrationTeamForm
from federation.forms.registration_player_form import RegistrationPlayerForm
from federation.models.team import Team
from federation.models.player import Player
from django.contrib.auth.models import User
from django.contrib import messages
from transliterate import translit
import datetime


def register_team(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    is_registration_opened = tournament.is_registration_opened()

    team_registration_form = RegistrationTeamForm(tournament=tournament)

    if request.method == "POST":
        team_registration_form = RegistrationTeamForm(request.POST, tournament=tournament)
        if team_registration_form.is_valid():
            player_ids = list(reversed(team_registration_form.verified_player_ids))
            team = Team.get_or_create_for_players(player_ids=player_ids)
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


def register_player(request):
    player_registration_form = RegistrationPlayerForm()

    if request.method == "POST":
        player_registration_form = RegistrationPlayerForm(request.POST)
        if player_registration_form.is_valid():
            try:
                user_name = player_registration_form.cleaned_data['name']+player_registration_form.cleaned_data['surname']
                user_name = translit(user_name, 'ru', reversed=True)
                password = player_registration_form.cleaned_data['surname']+str(datetime.datetime.now())

                user = User.objects.create_user(username=user_name, password=password)

                player = Player(
                    user=user,
                    name=player_registration_form.cleaned_data['name'],
                    surname=player_registration_form.cleaned_data['surname'],
                    birth_date=player_registration_form.cleaned_data['birth_date'],
                    country=player_registration_form.cleaned_data['country'],
                    gender=player_registration_form.cleaned_data['gender'],
                )
                player.save()

                messages.success(request, 'Спортсмена зареєстровано.', extra_tags='success')
                return redirect('player', id=player.pk)
            except Exception as e:
                messages.error(request, str(e), extra_tags='danger')
        else:
            for error_message in player_registration_form.errors:
                messages.error(request, player_registration_form.errors[error_message], extra_tags='danger')

    return render(request, 'register/player.html', {
        'player_registration_form': player_registration_form,
        'page_title': "Реєстрація спортсмена",
    })