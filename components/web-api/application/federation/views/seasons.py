import datetime
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from federation.models.season import Season
from federation.views.players import (
    DEFAULT_PLAYERS_PAGE_SIZE,
    PLAYER_AGE_CATEGORIES,
    PLAYERS_PAGE_SIZE_OPTIONS,
    PLAYERS_PAGE_SIZE_PARAM,
    _get_player_page_size,
    _pagination_pages,
    _player_pagination_summary,
)


def seasons(request, year=None):
    years = _get_available_years()
    selected_year = _get_selected_year(year, years)
    rating_field = 'rating'

    season_rows = (
        Season.objects
        .filter(year=selected_year, **{rating_field + '__gt': 0})
        .select_related('player', 'player__current_club', 'club', 'club__city')
    )

    player_filters = _get_season_filters(request)
    filter_options = _get_season_filter_options(season_rows)
    season_rows = _apply_season_filters(season_rows, player_filters, selected_year)
    season_rows = _order_season_rows(season_rows, rating_field)

    paginator = Paginator(season_rows, player_filters['page_size'])
    page_obj = paginator.get_page(request.GET.get('page'))
    _assign_season_display_ranks(page_obj)

    return render(request, 'seasons/seasons.html', {
        'players': page_obj.object_list,
        'years': _season_year_urls(player_filters, years),
        'year': str(selected_year),
        'rating_field': rating_field,
        'rating_power_field': '',
        'rating_filters': rating_field + "," + str(selected_year),
        'show_power_column': False,
        'is_season_rating': True,
        'page_title': _("Season rating"),
        'page_obj': page_obj,
        'page_size': player_filters['page_size'],
        'page_size_options': PLAYERS_PAGE_SIZE_OPTIONS,
        'player_filters': player_filters,
        'player_filter_options': filter_options,
        'player_active_params': _active_season_filter_params(player_filters),
        'player_pagination_pages': _pagination_pages(page_obj),
        'player_pagination_summary': _player_pagination_summary(page_obj),
        'player_pagination_urls': _season_pagination_urls(request, player_filters, page_obj),
        'player_reset_url': _season_reset_url(request, player_filters),
    })


def _get_available_years():
    return list(
        Season.objects
        .order_by('-year')
        .values_list('year', flat=True)
        .distinct()
    )


def _get_selected_year(year, years):
    if year is None:
        return years[0] if years else datetime.date.today().year - 1

    try:
        return int(year)
    except (TypeError, ValueError):
        raise Http404


def _get_season_filters(request):
    return {
        'search': request.GET.get('q', '').strip(),
        'club': request.GET.get('club', '').strip(),
        'age': request.GET.get('age', '').strip(),
        'sex': request.GET.get('sex', '').strip(),
        'league': 'all',
        'page_size': _get_player_page_size(request),
    }


def _get_season_filter_options(queryset):
    clubs = (
        queryset
        .filter(club__isnull=False)
        .values_list('club__short_name', flat=True)
        .distinct()
        .order_by('club__short_name')
    )

    return {
        'clubs': [club for club in clubs if club],
        'ages': PLAYER_AGE_CATEGORIES.keys(),
        'sexes': (
            ('M', _('Men')),
            ('F', _('Women')),
        ),
    }


def _apply_season_filters(queryset, player_filters, year):
    search = player_filters['search']
    if search:
        queryset = queryset.filter(
            Q(player__name__icontains=search) |
            Q(player__surname__icontains=search) |
            Q(player__second_name__icontains=search) |
            Q(club__name__icontains=search) |
            Q(club__short_name__icontains=search)
        )

    if player_filters['club']:
        queryset = queryset.filter(club__short_name=player_filters['club'])

    if player_filters['sex'] in ('M', 'F'):
        queryset = queryset.filter(player__gender=player_filters['sex'])

    if player_filters['age'] in PLAYER_AGE_CATEGORIES:
        queryset = [
            item for item in queryset
            if _season_age_category_key(item.player, year) == player_filters['age']
        ]

    return queryset


def _order_season_rows(season_rows, rating_field):
    if isinstance(season_rows, list):
        return sorted(
            season_rows,
            key=lambda item: (
                -getattr(item, rating_field),
                item.player.surname or '',
                item.player.name or '',
                item.player.pk,
            )
        )

    return season_rows.order_by('-' + rating_field, 'player__surname', 'player__name', 'player__id')


def _assign_season_display_ranks(page_obj):
    start_index = page_obj.start_index()

    for offset, item in enumerate(page_obj.object_list):
        item.display_rank = start_index + offset


def _season_age_category_key(player, year):
    today = datetime.date(int(year), 12, 31)
    born = player.birth_date
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    for category, ages in PLAYER_AGE_CATEGORIES.items():
        if ages[0] <= age <= ages[1]:
            return category

    return ''


def _active_season_filter_params(player_filters):
    params = {}
    for key in ('search', 'club', 'age', 'sex'):
        value = player_filters[key]
        if value:
            params['q' if key == 'search' else key] = value

    if player_filters.get('page_size') != DEFAULT_PLAYERS_PAGE_SIZE:
        params[PLAYERS_PAGE_SIZE_PARAM] = player_filters['page_size']

    return params


def _season_url(request, player_filters, page=None):
    params = _active_season_filter_params(player_filters)
    if page and page != 1:
        params['page'] = page

    query = urlencode(params)
    if not query:
        return request.path

    return '{}?{}'.format(request.path, query)


def _season_reset_url(request, player_filters):
    if player_filters.get('page_size') == DEFAULT_PLAYERS_PAGE_SIZE:
        return request.path

    return '{}?{}'.format(
        request.path,
        urlencode({PLAYERS_PAGE_SIZE_PARAM: player_filters['page_size']}),
    )


def _season_pagination_urls(request, player_filters, page_obj):
    return {
        'first': _season_url(request, player_filters, 1),
        'previous': _season_url(request, player_filters, page_obj.previous_page_number()) if page_obj.has_previous() else '#',
        'next': _season_url(request, player_filters, page_obj.next_page_number()) if page_obj.has_next() else '#',
        'last': _season_url(request, player_filters, page_obj.paginator.num_pages),
        'pages': {
            page: _season_url(request, player_filters, page)
            for page in _pagination_pages(page_obj)
            if page != 'ellipsis'
        },
    }


def _season_year_urls(player_filters, years):
    params = _active_season_filter_params(player_filters)
    query = urlencode(params)
    suffix = '?' + query if query else ''

    return [
        {
            'year': str(year),
            'url': '/seasons/{}{}'.format(year, suffix),
        }
        for year in years
    ]
