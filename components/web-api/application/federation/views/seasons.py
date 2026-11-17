import datetime
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.vary import vary_on_headers

from federation.models.season import Season
from federation.utils.pagination import pagination_links
from federation.views.players import (
    PLAYER_AGE_CATEGORIES,
    PLAYERS_PAGE_SIZE_OPTIONS,
    _active_player_filter_params,
    _get_player_filters,
    _player_pagination_summary,
    _rating_filter_fields,
)


@vary_on_headers("Sec-CH-UA-Mobile", "User-Agent")
def seasons(request, year=None):
    years = _get_available_years()
    selected_year = _get_selected_year(year, years)
    rating_field = 'rating'

    season_rows = _season_rating_queryset(selected_year, rating_field)
    ranking_rows = _order_season_rows(season_rows, rating_field)

    player_filters = _get_player_filters(request)
    filter_fields = _rating_filter_fields(season_rows, player_filters, "club")
    season_rows = _apply_season_filters(season_rows, player_filters, selected_year)
    season_rows = _order_season_rows(season_rows, rating_field)

    paginator = Paginator(season_rows, player_filters['page_size'])
    page_obj = paginator.get_page(request.GET.get('page'))
    page_rows = list(page_obj.object_list)
    _assign_season_display_ranks(page_rows, ranking_rows)
    page_obj.object_list = page_rows

    active_filters = _active_player_filter_params(player_filters)
    return render(request, 'seasons/seasons.html', {
        'players': page_rows,
        'ratings_pilot': True,
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
        'filter_fields': filter_fields,
        'active_filters': active_filters,
        'pagination_summary': _player_pagination_summary(page_obj),
        **pagination_links(page_obj, request.path, active_filters),
    })


def _season_rating_queryset(year, rating_field):
    return (
        Season.objects
        .filter(
            year=year,
            player__isnull=False,
            club__isnull=False,
            **{rating_field + '__gt': 0},
        )
        .select_related('player', 'player__current_club', 'club', 'club__city')
    )


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


def _assign_season_display_ranks(items, ranking_rows):
    rank_by_id = {
        row_id: rank
        for rank, row_id in enumerate(_season_row_ids(ranking_rows), start=1)
    }

    for item in items:
        item.display_rank = rank_by_id.get(item.pk, '')


def _season_row_ids(rows):
    if isinstance(rows, list):
        return [row.pk for row in rows]

    return rows.values_list('pk', flat=True)


def _season_age_category_key(player, year):
    today = datetime.date(int(year), 12, 31)
    born = player.birth_date
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    for category, ages in PLAYER_AGE_CATEGORIES.items():
        if ages[0] <= age <= ages[1]:
            return category

    return ''


def _season_year_urls(player_filters, years):
    params = _active_player_filter_params(player_filters)
    query = urlencode(params)
    suffix = '?' + query if query else ''

    return [
        {
            'year': str(year),
            'url': '/seasons/{}{}'.format(year, suffix),
        }
        for year in years
    ]
