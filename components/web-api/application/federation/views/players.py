import datetime
import json
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models import Prefetch
from django.db.models import Q
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from federation.models.player import Player
from federation.models.tournament import TeamTournamentMembership
from federation.models.tournament import Tournament
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.views.decorators.vary import vary_on_headers
from federation.helpers.general import get_model
from federation.utils.pagination import pagination_links
from federation.utils.rankings import attach_rating_positions
from federation.utils.request_devices import is_phone_request
from federation.utils.tournament_names import get_tournament_card_metadata
from federation.utils.tournament_names import get_tournament_display_name


PLAYERS_PAGE_SIZE_PARAM = 'per_page'
DEFAULT_PLAYERS_PAGE_SIZE = 50
MOBILE_PLAYERS_PAGE_SIZE = 25
PLAYERS_PAGE_SIZE_OPTIONS = (MOBILE_PLAYERS_PAGE_SIZE, 30, DEFAULT_PLAYERS_PAGE_SIZE, 100)
PLAYER_HISTORY_PAGE_SIZES = (*PLAYERS_PAGE_SIZE_OPTIONS, -1)
PLAYER_HISTORY_SORT_DEFAULTS = {'date': 'desc', 'place': 'asc', 'points': 'desc'}
PLAYER_AGE_CATEGORIES = {
    'JUN': (0, 18),
    'ESP': (19, 23),
    'SEN': (24, 55),
    'VET': (56, 1000),
}


@vary_on_headers("Sec-CH-UA-Mobile", "User-Agent")
def players(request, licence_filter=None, rating_filter=None):

    players_objects = Player.objects.select_related('current_club', 'current_club__city')
    if licence_filter == 'licence':
        players_objects = Player.get_actual_players_list().select_related('current_club', 'current_club__city')
    elif licence_filter == 'inclusive':
        players_objects = players_objects.filter(is_inclusive=True)

    rating_field = 'current_rating'
    rating_power_field = 'current_power'
    if rating_filter == 'b':
        rating_field = 'current_rating_b'
        rating_power_field = 'current_power_b'
    elif rating_filter == 'liga':
        rating_field = 'current_rating_liga'
    elif rating_filter == 'inclusive':
        rating_field = 'current_rating_inclusive'
        rating_power_field = 'current_power_inclusive'

    player_filters = _get_player_filters(request)
    filter_fields = _rating_filter_fields(players_objects, player_filters, "current_club")
    players_objects = _apply_player_filters(players_objects, player_filters)
    players_objects = _order_players(players_objects, rating_field)

    paginator = Paginator(players_objects, player_filters['page_size'])
    page_obj = paginator.get_page(request.GET.get('page'))
    page_players = list(page_obj.object_list)
    attach_rating_positions(
        page_players,
        rating_field,
        _player_ranking_queryset(licence_filter, rating_field),
    )

    active_filters = _active_player_filter_params(player_filters)
    return render(request, 'players/players.html', {
        'players': page_players,
        'ratings_pilot': True,
        'rating_filters': rating_field+","+str(licence_filter),
        'rating_field': rating_field,
        'rating_power_field': rating_power_field,
        'show_power_column': True,
        'page_title': _("Rating"),
        'page_obj': page_obj,
        'page_size': player_filters['page_size'],
        'page_size_options': PLAYERS_PAGE_SIZE_OPTIONS,
        'player_filters': player_filters,
        'filter_fields': filter_fields,
        'active_filters': active_filters,
        'pagination_summary': _player_pagination_summary(page_obj),
        **pagination_links(page_obj, request.path, active_filters),
    })


def _get_player_filters(request):
    page_size_override = _requested_player_page_size(request)
    return {
        'search': request.GET.get('q', '').strip(),
        'club': request.GET.get('club', '').strip(),
        'age': request.GET.get('age', '').strip(),
        'sex': request.GET.get('sex', '').strip(),
        'page_size': page_size_override or _default_player_page_size(request),
        'page_size_override': page_size_override,
    }


def _requested_player_page_size(request):
    try:
        page_size = int(request.GET.get(PLAYERS_PAGE_SIZE_PARAM, ''))
    except ValueError:
        return None

    return page_size if page_size in PLAYERS_PAGE_SIZE_OPTIONS else None


def _default_player_page_size(request):
    return MOBILE_PLAYERS_PAGE_SIZE if is_phone_request(request) else DEFAULT_PLAYERS_PAGE_SIZE


def _apply_player_filters(queryset, player_filters):
    search = player_filters['search']
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(surname__icontains=search) |
            Q(second_name__icontains=search) |
            Q(current_club__name__icontains=search) |
            Q(current_club__short_name__icontains=search)
        )

    if player_filters['club']:
        queryset = queryset.filter(current_club__short_name=player_filters['club'])

    if player_filters['sex'] in ('M', 'F'):
        queryset = queryset.filter(gender=player_filters['sex'])

    if player_filters['age'] in PLAYER_AGE_CATEGORIES:
        queryset = [
            player for player in queryset
            if _player_age_category_key(player) == player_filters['age']
        ]

    return queryset


def _order_players(players_objects, rating_field):
    if isinstance(players_objects, list):
        return sorted(
            players_objects,
            key=lambda player: (
                -getattr(player, rating_field),
                player.surname or '',
                player.name or '',
                player.pk,
            )
        )

    return players_objects.order_by('-' + rating_field, 'surname', 'name', 'id')


def _player_ranking_queryset(licence_filter, rating_field):
    if licence_filter in ('licence', 'inclusive'):
        if rating_field == 'current_rating_inclusive':
            return Player.objects.filter(is_inclusive=True)

        return Player.get_actual_players_list()

    return Player.objects.all()


def _rating_filter_fields(queryset, filters, club_relation):
    club_name = f'{club_relation}__short_name'
    clubs = (
        queryset.filter(**{f'{club_relation}__isnull': False})
        .values_list(club_name, flat=True)
        .distinct()
        .order_by(club_name)
    )

    return (
        {
            'name': 'club', 'label': _("Club"), 'placeholder': _("All clubs"), 'icon': 'bi-building',
            'options': [(club, club) for club in clubs if club], 'selected': filters['club'],
        },
        {
            'name': 'age', 'label': _("Age"), 'placeholder': _("All age categories"), 'icon': 'bi-people',
            'options': [(age, age) for age in PLAYER_AGE_CATEGORIES],
            'selected': filters['age'],
        },
        {
            'name': 'sex', 'label': _("Sex"), 'placeholder': _("All athletes"), 'icon': 'bi-gender-ambiguous',
            'options': (('M', _("Men")), ('F', _("Women"))), 'selected': filters['sex'],
        },
    )


def _player_age_category_key(player):
    today = datetime.date.today()
    born = player.birth_date
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    for category, ages in PLAYER_AGE_CATEGORIES.items():
        if ages[0] <= age <= ages[1]:
            return category

    return ''


def _active_player_filter_params(player_filters):
    params = {}
    for key in ('search', 'club', 'age', 'sex'):
        value = player_filters[key]
        if value:
            params['q' if key == 'search' else key] = value

    if player_filters['page_size_override']:
        params[PLAYERS_PAGE_SIZE_PARAM] = player_filters['page_size_override']

    return params


def _player_pagination_summary(page_obj):
    if page_obj.paginator.count == 0:
        return _("Showing 0 of 0 athletes")

    return (
        _("Showing _START_ to _END_ of _TOTAL_ athletes")
        .replace('_START_', str(page_obj.start_index()))
        .replace('_END_', str(page_obj.end_index()))
        .replace('_TOTAL_', str(page_obj.paginator.count))
    )


@vary_on_headers('Sec-CH-UA-Mobile', 'User-Agent')
def player(request, id):
    player = get_object_or_404(
        Player.objects.select_related('current_club', 'current_club__city'),
        pk=id,
    )

    all_past_tournaments = Tournament.get_list_by_player(player=player, date_filter='past').distinct()
    past_tournaments = (
        Tournament.get_list_by_player(player=player, date_filter='past', type_filter='except_b')
        .distinct()
        .order_by('-start_date', '-pk')
    )
    past_b_tournaments = Tournament.get_list_by_player(player=player, date_filter='past', type_filter='b').distinct()
    past_away_tournaments = Tournament.get_list_by_player(player=player, date_filter='past', type_filter='away').distinct()

    today = datetime.datetime.now()
    current_year = today.year

    this_year_tournaments_count = all_past_tournaments.filter(start_date__year=current_year).count()
    this_year_b_tournaments_count = past_b_tournaments.filter(start_date__year=current_year).count()
    this_year_liga_tournaments_count = all_past_tournaments.filter(start_date__year=current_year, is_ukrainian_league=True).count()
    this_year_rating_tournaments_count = all_past_tournaments.filter(start_date__year=current_year, is_goes_to_rating=True).count()
    this_year_away_tournaments_count = past_away_tournaments.filter(start_date__year=current_year).count()
    player_rating_position = None
    if player.is_licence_active and player.licence_number:
        player_rating_position = player.get_ranking('current_rating')

    player_summary_info = {
        'this_year_tournaments_count': this_year_tournaments_count,
        'this_year_b_tournaments_count': this_year_b_tournaments_count,
        'this_year_liga_tournaments_count': this_year_liga_tournaments_count,
        'this_year_rating_tournaments_count': this_year_rating_tournaments_count,
        'this_year_away_tournaments_count': this_year_away_tournaments_count,
    }

    season_rating_field = "rating"
    seasons_model = get_model('Season')
    player_seasons = seasons_model.objects.filter(player=player).order_by('-year')

    from federation.models.national_teams import PlayerNational_teamMembership
    is_national_team_player = PlayerNational_teamMembership.objects.filter(player=player).exists()
    player_tournament_rows = _build_player_tournament_rows(player, past_tournaments)

    return render(request, 'players/player.html', {
        'player': player,
        'player_summary_info': player_summary_info,
        'player_rating_position': player_rating_position,
        **_paginate_player_history(request, player_tournament_rows),
        'is_national_team_player': is_national_team_player,
        'season_rating_field': season_rating_field,
        'player_seasons': player_seasons,
    })


def _paginate_player_history(request, rows):
    sort = request.GET.get('sort', 'date')
    if sort not in PLAYER_HISTORY_SORT_DEFAULTS:
        sort = 'date'
    direction = request.GET.get('direction', PLAYER_HISTORY_SORT_DEFAULTS[sort])
    if direction not in ('asc', 'desc'):
        direction = PLAYER_HISTORY_SORT_DEFAULTS[sort]
    descending = direction == 'desc'

    if sort == 'place':
        def place_key(row):
            place = int(row['place'] or 0)
            if place <= 0:
                return (True,)
            place_max = int(row['place_max'] or place)
            return (False, -place if descending else place,
                    -row['tournament'].start_date.toordinal(),
                    -place_max if descending else place_max,
                    row['teams_count'] if descending else -row['teams_count'])

        rows.sort(key=place_key)
    elif sort == 'points':
        rows.sort(key=lambda row: row['team_rating_points'] or 0, reverse=descending)
    else:
        rows.sort(key=lambda row: row['tournament'].start_date, reverse=descending)

    try:
        page_size = int(request.GET.get('per_page', ''))
    except ValueError:
        page_size = None
    filters = {}
    if sort != 'date' or direction != 'desc':
        filters.update(sort=sort, direction=direction)
    if page_size in PLAYER_HISTORY_PAGE_SIZES:
        filters['per_page'] = page_size
    else:
        page_size = _default_player_page_size(request)

    paginator = Paginator(rows, max(len(rows), 1) if page_size == -1 else page_size)
    page_obj = paginator.get_page(request.GET.get('page'))
    headings = {}
    for field, default in PLAYER_HISTORY_SORT_DEFAULTS.items():
        active = field == sort
        next_direction = ('asc' if descending else 'desc') if active else default
        query = urlencode(dict(filters, sort=field, direction=next_direction))
        headings[field] = {
            'url': f'{request.path}?{query}#player-history',
            'direction': ('descending' if descending else 'ascending') if active else '',
        }

    return {
        'player_tournament_rows': page_obj.object_list,
        'history_headings': headings,
        'page_obj': page_obj,
        'page_size': page_size,
        'page_size_options': PLAYER_HISTORY_PAGE_SIZES,
        'active_filters': filters,
        'pagination_summary': _('Showing 0 of 0 competitions') if not rows else (
            _('Showing _START_ to _END_ of _TOTAL_ competitions')
            .replace('_START_', str(page_obj.start_index()))
            .replace('_END_', str(page_obj.end_index()))
            .replace('_TOTAL_', str(paginator.count))
        ),
        **pagination_links(page_obj, request.path, filters),
    }


def _build_player_tournament_rows(player, tournaments):
    tournaments = list(tournaments)
    tournament_ids = [tournament.pk for tournament in tournaments]

    if not tournament_ids:
        return []

    memberships = (
        TeamTournamentMembership.objects
        .filter(tournament_id__in=tournament_ids, team__players=player)
        .select_related('team', 'tournament')
        .prefetch_related(
            Prefetch(
                'team__players',
                queryset=Player.objects.order_by('surname', 'name'),
                to_attr='ordered_players',
            )
        )
        .order_by('id')
    )
    memberships_by_tournament_id = {}
    for membership in memberships:
        memberships_by_tournament_id.setdefault(membership.tournament_id, membership)

    actual_team_counts = {
        row['tournament_id']: row['teams_count']
        for row in (
            TeamTournamentMembership.objects
            .filter(tournament_id__in=tournament_ids)
            .values('tournament_id')
            .annotate(teams_count=Count('id'))
        )
    }

    rating_tournament_ids = _player_rating_tournament_ids(player)
    rows = []
    for tournament in tournaments:
        membership = memberships_by_tournament_id.get(tournament.pk)
        team = membership.team if membership else None
        team_players = list(getattr(team, 'ordered_players', [])) if team else []

        if not team_players and team:
            team_players = list(team.players.all())

        place_min, place_max, place_label = _membership_place_data(membership)
        rows.append({
            'tournament': tournament,
            'title': get_tournament_display_name(tournament),
            'metadata': get_tournament_card_metadata(tournament),
            'team': team,
            'team_players': team_players,
            'place': place_min,
            'place_max': place_max,
            'place_label': place_label,
            'tournament_power': tournament.power,
            'team_power': membership.power if membership else None,
            'team_rating_points': membership.rating_points if membership else None,
            'teams_count': _resolved_tournament_teams_count(tournament, actual_team_counts),
            'is_rating_relevant': tournament.pk in rating_tournament_ids,
        })

    return rows


def _membership_place_data(membership):
    if not membership:
        return '', '', ''

    place_min = membership.place_min or 0
    place_max = membership.place_max or 0
    if place_max > place_min:
        return str(place_min), str(place_max), '{}-{}'.format(place_min, place_max)

    return str(place_min), str(place_min), str(place_min)


def _resolved_tournament_teams_count(tournament, actual_team_counts):
    if tournament.total_number_of_teams and tournament.total_number_of_teams > 0:
        return tournament.total_number_of_teams

    return actual_team_counts.get(tournament.pk, 0)


def _player_rating_tournament_ids(player):
    if not player.current_rating_tournaments:
        return set()

    try:
        tournaments = json.loads(player.current_rating_tournaments)
    except (TypeError, ValueError):
        return set()

    return {
        tournament.get('tournament')
        for tournament in tournaments
        if tournament.get('tournament')
    }
