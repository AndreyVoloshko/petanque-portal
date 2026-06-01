import datetime
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from federation.models.player import Player
from federation.models.tournament import Tournament
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from federation.helpers.general import get_model


PLAYERS_PAGE_SIZE_PARAM = 'per_page'
DEFAULT_PLAYERS_PAGE_SIZE = 50
PLAYERS_PAGE_SIZE_OPTIONS = (25, 30, 50, 100)
PLAYER_AGE_CATEGORIES = {
    'JUN': (0, 18),
    'ESP': (19, 23),
    'SEN': (24, 55),
    'VET': (56, 1000),
}


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
    filter_options = _get_player_filter_options(players_objects)
    players_objects = _apply_player_filters(players_objects, player_filters)
    players_objects = _order_players(players_objects, rating_field)

    paginator = Paginator(players_objects, player_filters['page_size'])
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'players/players.html', {
        'players': page_obj.object_list,
        'rating_filters': rating_field+","+str(licence_filter),
        'rating_field': rating_field,
        'rating_power_field': rating_power_field,
        'page_title': _("Rating"),
        'page_obj': page_obj,
        'page_size': player_filters['page_size'],
        'page_size_options': PLAYERS_PAGE_SIZE_OPTIONS,
        'player_filters': player_filters,
        'player_filter_options': filter_options,
        'player_active_params': _active_player_filter_params(player_filters),
        'player_pagination_pages': _pagination_pages(page_obj),
        'player_pagination_summary': _player_pagination_summary(page_obj),
        'player_pagination_urls': _player_pagination_urls(request, player_filters, page_obj),
        'player_reset_url': _player_reset_url(request, player_filters),
    })


def _get_player_filters(request):
    return {
        'search': request.GET.get('q', '').strip(),
        'club': request.GET.get('club', '').strip(),
        'age': request.GET.get('age', '').strip(),
        'sex': request.GET.get('sex', '').strip(),
        'page_size': _get_player_page_size(request),
    }


def _get_player_page_size(request):
    try:
        page_size = int(request.GET.get(PLAYERS_PAGE_SIZE_PARAM, DEFAULT_PLAYERS_PAGE_SIZE))
    except (TypeError, ValueError):
        return DEFAULT_PLAYERS_PAGE_SIZE

    if page_size in PLAYERS_PAGE_SIZE_OPTIONS:
        return page_size

    return DEFAULT_PLAYERS_PAGE_SIZE


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


def _get_player_filter_options(queryset):
    clubs = (
        queryset
        .filter(current_club__isnull=False)
        .values_list('current_club__short_name', flat=True)
        .distinct()
        .order_by('current_club__short_name')
    )

    return {
        'clubs': [club for club in clubs if club],
        'ages': PLAYER_AGE_CATEGORIES.keys(),
        'sexes': (
            ('M', _('Men')),
            ('F', _('Women')),
        ),
    }


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

    if player_filters.get('page_size') != DEFAULT_PLAYERS_PAGE_SIZE:
        params[PLAYERS_PAGE_SIZE_PARAM] = player_filters['page_size']

    return params


def _player_url(request, player_filters, page=None):
    params = _active_player_filter_params(player_filters)
    if page and page != 1:
        params['page'] = page

    query = urlencode(params)
    if not query:
        return request.path

    return '{}?{}'.format(request.path, query)


def _player_reset_url(request, player_filters):
    if player_filters.get('page_size') == DEFAULT_PLAYERS_PAGE_SIZE:
        return request.path

    return '{}?{}'.format(
        request.path,
        urlencode({PLAYERS_PAGE_SIZE_PARAM: player_filters['page_size']}),
    )


def _player_pagination_urls(request, player_filters, page_obj):
    return {
        'first': _player_url(request, player_filters, 1),
        'previous': _player_url(request, player_filters, page_obj.previous_page_number()) if page_obj.has_previous() else '#',
        'next': _player_url(request, player_filters, page_obj.next_page_number()) if page_obj.has_next() else '#',
        'last': _player_url(request, player_filters, page_obj.paginator.num_pages),
        'pages': {
            page: _player_url(request, player_filters, page)
            for page in _pagination_pages(page_obj)
            if page != 'ellipsis'
        },
    }


def _pagination_pages(page_obj):
    current = page_obj.number
    total = page_obj.paginator.num_pages
    pages = []

    for page in range(1, total + 1):
        if page == 1 or page == total or abs(page - current) <= 1:
            pages.append(page)
        elif pages[-1] != 'ellipsis':
            pages.append('ellipsis')

    return pages


def _player_pagination_summary(page_obj):
    if page_obj.paginator.count == 0:
        return _("Showing 0 of 0 athletes")

    return (
        _("Showing _START_ to _END_ of _TOTAL_ athletes")
        .replace('_START_', str(page_obj.start_index()))
        .replace('_END_', str(page_obj.end_index()))
        .replace('_TOTAL_', str(page_obj.paginator.count))
    )


def player(request, id):
    player = get_object_or_404(Player, pk=id)

    all_past_tournaments = Tournament.get_list_by_player(player=player, date_filter='past').distinct()
    past_tournaments = Tournament.get_list_by_player(player=player, date_filter='past', type_filter='except_b').distinct()
    past_b_tournaments = Tournament.get_list_by_player(player=player, date_filter='past', type_filter='b').distinct()
    future_tournaments = Tournament.get_list_by_player(player=player, date_filter='future').distinct()
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
    national_team_memberships = PlayerNational_teamMembership.objects.filter(player=player).select_related('team')

    return render(request, 'players/player.html', {
        'player': player,
        'player_summary_info': player_summary_info,
        'player_rating_position': player_rating_position,
        'past_tournaments': past_tournaments,
        'future_tournaments': future_tournaments,
        'past_b_tournaments': past_b_tournaments,
        'past_away_tournaments': past_away_tournaments,
        'player_tournaments': past_tournaments,
        'national_team_memberships': national_team_memberships,
        'season_rating_field': season_rating_field,
        'player_seasons': player_seasons,
    })
