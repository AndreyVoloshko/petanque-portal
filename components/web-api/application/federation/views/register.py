import re

from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.contrib.auth import login
from django.db import transaction
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from federation.forms.registration_team_form import RegistrationTeamForm
from federation.forms.registration_player_form import RegistrationPlayerForm
from federation.models.team import Team
from federation.models.player import Player
from federation.models.email_confirmation import EmailConfirmation
from federation.utils.email import send_confirmation_email
from federation.utils.autocaptcha import DEFAULT_ACTION as AUTOCAPTCHA_ACTION, get_public_key as get_autocaptcha_public_key
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from transliterate import translit


def generate_username(name, surname):
    raw_username = '{}{}'.format(name, surname).replace(' ', '')
    try:
        base_username = translit(raw_username, 'ru', reversed=True)
    except Exception:
        base_username = raw_username

    base_username = re.sub(r'[^A-Za-z0-9_@.+-]', '', base_username) or 'player'
    base_username = base_username[:140]
    username = base_username
    counter = 1
    while User.objects.filter(username=username).exists():
        suffix = str(counter)
        username = '{}{}'.format(base_username[:150 - len(suffix)], suffix)
        counter += 1
    return username


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
            messages.success(request, _('Team registered.'), extra_tags='success')
            return redirect('tournament', id=tournament.pk)
        else:
            for error_message in team_registration_form.errors:
                messages.error(request, team_registration_form.errors[error_message], extra_tags='danger')

    return render(request, 'register/team.html', {
        'tournament': tournament,
        'is_registration_opened': is_registration_opened,
        'team_registration_form': team_registration_form,
        'page_title': _("Team registration"),
    })


def register_player(request):
    player_registration_form = RegistrationPlayerForm(request=request)

    if request.method == "POST":
        player_registration_form = RegistrationPlayerForm(request.POST, request=request)
        if player_registration_form.is_valid():
            try:
                email = player_registration_form.cleaned_data.get('email') or ''
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=generate_username(
                            player_registration_form.cleaned_data['name'],
                            player_registration_form.cleaned_data['surname'],
                        ),
                        email=email,
                        password=player_registration_form.cleaned_data['password'],
                    )

                    player = Player(
                        user=user,
                        name=player_registration_form.cleaned_data['name'],
                        surname=player_registration_form.cleaned_data['surname'],
                        second_name=player_registration_form.cleaned_data.get('patronymic') or '',
                        birth_date=player_registration_form.cleaned_data['birth_date'],
                        country=player_registration_form.cleaned_data['country'],
                        gender=player_registration_form.cleaned_data['gender'],
                        licence_number=player_registration_form.cleaned_data.get('licence_number') or None,
                    )
                    player.save()

                    confirmation = None
                    if email:
                        confirmation = EmailConfirmation.objects.create(user=user, email=email)

                if confirmation:
                    send_confirmation_email(request, user, confirmation)
                    messages.success(
                        request,
                        _('Registration successful. Check your inbox to confirm your email.'),
                        extra_tags='success',
                    )
                else:
                    messages.success(request, _('Registration successful!'), extra_tags='success')

                login(request, user)
                return redirect('profile')
            except Exception as e:
                messages.error(request, str(e), extra_tags='danger')
        else:
            for error_message in player_registration_form.errors:
                messages.error(request, player_registration_form.errors[error_message], extra_tags='danger')

    return render(request, 'register/player.html', {
        'player_registration_form': player_registration_form,
        'autocaptcha_public_key': get_autocaptcha_public_key(),
        'autocaptcha_action': AUTOCAPTCHA_ACTION,
        'page_title': _("Player registration"),
    })
