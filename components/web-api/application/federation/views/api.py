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
    SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME,
    SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME,
    get_or_create_system_audit_user,
    record_model_change,
    record_tournament_team_places_change,
)
from federation.models.tournament import Tournament, TeamTournamentMembership
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


# The external draw tool owns three tournament attributes. They are writable
# only here, authenticated by the shared API password (no session, no CSRF).
TOURNAMENT_META_MAX_BYTES = 256 * 1024
TOURNAMENT_META_REQUIRED_KEYS = {'games', 'teams'}
TOURNAMENT_API_ATTRIBUTES = ('meta', 'petanque_draw_id', 'teams')


def _validate_meta(meta):
    """Return (serialized_meta, error). Accepts a draw object or its JSON text."""
    if isinstance(meta, str):
        try:
            parsed = json.loads(meta)
        except (json.JSONDecodeError, ValueError):
            return None, 'meta must be valid JSON'
        raw = meta
    elif isinstance(meta, dict):
        parsed = meta
        raw = json.dumps(meta, ensure_ascii=False)
    else:
        return None, 'meta must be a draw object'

    if not isinstance(parsed, dict) or not TOURNAMENT_META_REQUIRED_KEYS <= parsed.keys():
        return None, 'meta must be a draw object containing "games" and "teams"'

    if len(raw.encode('utf-8')) > TOURNAMENT_META_MAX_BYTES:
        return None, 'meta is too large'

    return raw, None


def _apply_team_places(tournament, teams):
    """Lock and validate the whole submission before writing any place."""
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
            return None, f'teams[{i}]: team {team["team_id"]} is not registered in this tournament'

    before_memberships = [copy(membership) for membership in locked_memberships]
    updated = []
    for team in teams:
        membership = memberships[team['team_id']]
        membership.place_min = team['place_min']
        membership.place_max = team.get('place_max') or 0
        membership.save()
        updated.append(team['team_id'])

    record_tournament_team_places_change(
        get_or_create_system_audit_user(SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME),
        tournament,
        before_memberships,
        locked_memberships,
    )
    return updated, None


class _ApiError(Exception):
    """Abort the transaction and return `response` to the caller."""

    def __init__(self, response):
        self.response = response


@csrf_exempt
@require_POST
def update_tournament(request):
    """Update the draw-owned tournament attributes: meta, petanque_draw_id, teams.

    Serves both `/api/tournament/` and the legacy `/api/tournament/results/`.
    Every provided attribute is validated before anything is written, and the
    whole request is applied in one transaction: a rejected team rolls back the
    meta and draw-id writes that accompanied it.
    """
    if not settings.API_PASSWORD or request.headers.get('Authorization') != settings.API_PASSWORD:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return _bad_request('Invalid JSON body')

    if not isinstance(body, dict):
        return _bad_request('Body must be an object')

    tournament_id = body.get('tournament_id')
    if tournament_id is None:
        return _bad_request('tournament_id is required')

    if not any(attribute in body for attribute in TOURNAMENT_API_ATTRIBUTES):
        return _bad_request(
            'at least one of "meta", "petanque_draw_id" or "teams" is required'
        )

    raw_meta = None
    if 'meta' in body:
        raw_meta, error = _validate_meta(body['meta'])
        if error:
            return _bad_request(error)

    draw_id = None
    if 'petanque_draw_id' in body:
        draw_id = body['petanque_draw_id']
        if not isinstance(draw_id, str):
            return _bad_request('petanque_draw_id must be a string')

    teams = None
    if 'teams' in body:
        teams = body['teams']
        if not isinstance(teams, list) or len(teams) == 0:
            return _bad_request('teams must be a non-empty array')
        for i, team in enumerate(teams):
            error = _validate_team_entry(team, i)
            if error:
                return _bad_request(error)

    updated_teams = []
    try:
        with transaction.atomic():
            try:
                tournament = Tournament.objects.select_for_update().get(pk=tournament_id)
            except (Tournament.DoesNotExist, ValueError, TypeError):
                raise _ApiError(JsonResponse({'error': 'Tournament not found'}, status=404))

            updated_fields = []
            if raw_meta is not None:
                if tournament.is_processing_closed():
                    raise _ApiError(JsonResponse(
                        {'error': 'tournament processing is closed'}, status=403,
                    ))
                updated_fields.append('meta')
            if draw_id is not None:
                updated_fields.append('petanque_draw_id')

            if updated_fields:
                tournament_before = copy(tournament)
                if raw_meta is not None:
                    tournament.meta = raw_meta
                if draw_id is not None:
                    tournament.petanque_draw_id = draw_id
                tournament.save(update_fields=updated_fields)
                # The tool authenticates by header, not session: attribute the
                # change to the system user or the audit entry is dropped.
                record_model_change(
                    get_or_create_system_audit_user(SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME),
                    tournament_before,
                    tournament,
                )

            if teams is not None:
                updated_teams, error = _apply_team_places(tournament, teams)
                if error:
                    raise _ApiError(_bad_request(error))
    except _ApiError as api_error:
        return api_error.response

    return JsonResponse({'status': 'ok', 'updated_teams': updated_teams})


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
