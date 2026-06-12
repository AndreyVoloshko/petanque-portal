import json
from copy import copy

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from federation.audit import (
    SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME,
    TOURNAMENT_CHANGE_FIELD_TEAM_PLACES,
    build_tournament_team_places_field_values,
    get_or_create_system_audit_user,
    log_model_change,
)
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from federation.models.player import Player
from federation.models.club import Club
from federation.utils.tournament_names import tournament_display_name_matches

def tournaments_list(request):
    start_date = parse_datetime(request.GET.get('start'))
    end_date = parse_datetime(request.GET.get('end'))
    data = []

    if start_date and end_date:

        tournaments = Tournament.get_list_by_dates_range(start_date, end_date)

        for tournament in tournaments:
            classes = "tournament "

            if tournament.is_goes_to_rating:
                classes += "tournament_goes_to_rating "

            if tournament.is_ukrainian_league:
                classes += "tournament_ukrainian_league "

            if tournament.is_b_tournament:
                classes += "tournament_b "

            classes += " tournament_" + str(tournament.category)

            item = {
                'id': tournament.pk,
                'url': reverse('tournament', kwargs={'id':tournament.pk}),
                'title': tournament.get_display_name(),
                'start': tournament.start_date,
                'end': tournament.start_date,
                'className': classes,
                'allDay': True,
            }

            if tournament.end_date:
                item['end'] = tournament.end_date

            data.append(item)

    return JsonResponse(data, safe=False)


def players_clubs_and_tournaments_list(request):
    template = request.GET.get('typedText')
    data = []

    if template:
        players = Player.objects.filter(Q(name__icontains=template) | Q(surname__icontains=template))
        clubs = Club.objects.filter(name__icontains=template)
        tournaments = [
            tournament for tournament in Tournament.public_queryset()
            if tournament_display_name_matches(tournament, template)
        ]

        for player in players:
            item = {
                'href': reverse('player', kwargs={'id':player.pk}),
                'value': player.get_name(),
                'disabled': 0,
            }

            data.append(item)

        for club in clubs:
            item = {
                'href': reverse('club', kwargs={'id':club.pk}),
                'value': club.name,
                'disabled': 0,
            }

            data.append(item)

        for tournament in tournaments:
            item = {
                'href': reverse('tournament', kwargs={'id':tournament.pk}),
                'value': tournament.get_display_name(),
                'disabled': 0,
            }

            data.append(item)

    return JsonResponse(data, safe=False)


def _bad_request(message):
    return JsonResponse({'error': message}, status=400)


def _validate_team_entry(team, index):
    prefix = f'teams[{index}]'
    if not isinstance(team, dict):
        return f'{prefix} must be an object'
    if team.get('team_id') is None:
        return f'{prefix}.team_id is required'
    if team.get('place_min') is None:
        return f'{prefix}.place_min is required'
    if not isinstance(team['place_min'], int):
        return f'{prefix}.place_min must be an integer'
    if 'place_max' in team and team['place_max'] is not None and not isinstance(team['place_max'], int):
        return f'{prefix}.place_max must be an integer'
    return None


@csrf_exempt
@require_POST
def submit_tournament_results(request):
    """Update submitted team places and record one revertable tournament change."""
    if not settings.API_PASSWORD or request.headers.get('Authorization') != settings.API_PASSWORD:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return _bad_request('Invalid JSON body')

    tournament_id = body.get('tournament_id')
    teams = body.get('teams')

    if tournament_id is None:
        return _bad_request('tournament_id is required')
    if not isinstance(teams, list) or len(teams) == 0:
        return _bad_request('teams must be a non-empty array')

    for i, team in enumerate(teams):
        error = _validate_team_entry(team, i)
        if error:
            return _bad_request(error)

    with transaction.atomic():
        try:
            tournament = Tournament.objects.select_for_update().get(pk=tournament_id)
        except Tournament.DoesNotExist:
            return JsonResponse({'error': 'Tournament not found'}, status=404)

        # Validate and lock the complete submission before applying any result
        # so a rejected request cannot leave unaudited partial updates.
        team_ids = [team['team_id'] for team in teams]
        locked_memberships = list(
            TeamTournamentMembership.objects.select_for_update().filter(
                tournament=tournament,
                team_id__in=team_ids,
            )
        )
        memberships = {
            membership.team_id: membership
            for membership in locked_memberships
        }
        for i, team in enumerate(teams):
            if team['team_id'] not in memberships:
                return _bad_request(f'teams[{i}]: team {team["team_id"]} is not registered in this tournament')

        before_memberships = [copy(membership) for membership in locked_memberships]
        updated = []
        for team in teams:
            membership = memberships[team['team_id']]
            membership.place_min = team['place_min']
            membership.place_max = team.get('place_max') or 0
            membership.save()
            updated.append(team['team_id'])

        field_values = build_tournament_team_places_field_values(before_memberships, locked_memberships)
        if field_values:
            log_model_change(
                get_or_create_system_audit_user(SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME),
                tournament,
                [TOURNAMENT_CHANGE_FIELD_TEAM_PLACES],
                field_values=field_values,
            )

    return JsonResponse({'updated_teams': updated})


def players_list(request):
    template = request.GET.get('q')

    data = {
        "results": [],
        "pagination": {
            "more": False
        }
    }

    if template:
        players = Player.objects.filter(Q(name__icontains=template) | Q(surname__icontains=template))
        for player in players:
            item = {
                'id': player.pk,
                'text': player.get_name(),
            }

            data['results'].append(item)

    return JsonResponse(data, safe=False)
