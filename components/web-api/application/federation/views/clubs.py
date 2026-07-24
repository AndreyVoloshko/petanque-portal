from decimal import Decimal
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Avg, Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from federation.models.club import Club
from federation.models.national_teams import PlayerNational_teamMembership
from federation.models.player import Player


CLUBS_PAGE_SIZE_PARAM = 'per_page'
DEFAULT_CLUBS_PAGE_SIZE = 25
CLUBS_PAGE_SIZE_OPTIONS = (25, 50, 100)
RATED_CLUB_PLAYER_FILTER = (
    Q(player__is_licence_active=True)
    & ~Q(player__licence_number__isnull=True)
    & ~Q(player__licence_number='')
)
CLUB_SORT_OPTIONS = (
    ('rating', _('Rating first')),
    ('athletes', _('Most athletes')),
    ('average', _('Best average')),
    ('name', _('Name A-Z')),
    ('founded', _('Newest clubs')),
)


def clubs(request):
    clubs_queryset = _clubs_queryset()
    club_filters = _get_club_filters(request)
    filter_options = _get_club_filter_options(clubs_queryset)
    clubs_queryset = _apply_club_filters(clubs_queryset, club_filters)
    clubs_queryset = _order_clubs(clubs_queryset, club_filters['sort'])

    paginator = Paginator(clubs_queryset, club_filters['page_size'])
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'clubs/clubs.html', {
        'clubs': page_obj.object_list,
        'page_title': _("Clubs"),
        'page_obj': page_obj,
        'page_size': club_filters['page_size'],
        'page_size_options': CLUBS_PAGE_SIZE_OPTIONS,
        'club_filters': club_filters,
        'club_filter_options': filter_options,
        'club_sort_options': CLUB_SORT_OPTIONS,
        'club_active_params': _active_club_filter_params(club_filters),
        'club_pagination_pages': _pagination_pages(page_obj),
        'club_pagination_summary': _club_pagination_summary(page_obj),
        'club_pagination_urls': _club_pagination_urls(request, club_filters, page_obj),
        'club_reset_url': _club_reset_url(request, club_filters),
    })


def _clubs_queryset():
    rating_output = DecimalField(max_digits=19, decimal_places=4)

    return (
        Club.objects
        .filter(is_active=True)
        .select_related('city', 'president')
        .annotate(
            total_rating=Coalesce(
                Sum('player__current_rating', filter=RATED_CLUB_PLAYER_FILTER),
                Value(Decimal('0.0000')),
                output_field=rating_output,
            ),
            average_rating=Coalesce(
                Avg('player__current_rating', filter=RATED_CLUB_PLAYER_FILTER),
                Value(Decimal('0.0000')),
                output_field=rating_output,
            ),
            players_count=Count('player', distinct=True),
        )
    )


def _get_club_filters(request):
    return {
        'search': request.GET.get('q', '').strip(),
        'city': request.GET.get('city', '').strip(),
        'year': request.GET.get('year', '').strip(),
        'sort': _get_club_sort(request),
        'page_size': _get_club_page_size(request),
    }


def _get_club_sort(request):
    sort = request.GET.get('sort', 'rating').strip()
    if sort in dict(CLUB_SORT_OPTIONS):
        return sort

    return 'rating'


def _get_club_page_size(request):
    try:
        page_size = int(request.GET.get(CLUBS_PAGE_SIZE_PARAM, DEFAULT_CLUBS_PAGE_SIZE))
    except (TypeError, ValueError):
        return DEFAULT_CLUBS_PAGE_SIZE

    if page_size in CLUBS_PAGE_SIZE_OPTIONS:
        return page_size

    return DEFAULT_CLUBS_PAGE_SIZE


def _get_club_filter_options(queryset):
    cities = (
        queryset
        .filter(city__isnull=False)
        .values_list('city__name', flat=True)
        .distinct()
        .order_by('city__name')
    )
    years = (
        queryset
        .dates('date_created', 'year', order='DESC')
    )

    return {
        'cities': [city for city in cities if city],
        'years': [str(date.year) for date in years],
    }


def _apply_club_filters(queryset, club_filters):
    search = club_filters['search']
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(short_name__icontains=search) |
            Q(city__name__icontains=search) |
            Q(president__name__icontains=search) |
            Q(president__surname__icontains=search)
        )

    if club_filters['city']:
        queryset = queryset.filter(city__name=club_filters['city'])

    if club_filters['year']:
        try:
            queryset = queryset.filter(date_created__year=int(club_filters['year']))
        except ValueError:
            pass

    return queryset


def _order_clubs(queryset, sort):
    if sort == 'athletes':
        return queryset.order_by('-players_count', '-total_rating', 'short_name', 'id')
    if sort == 'average':
        return queryset.order_by('-average_rating', '-total_rating', 'short_name', 'id')
    if sort == 'name':
        return queryset.order_by('short_name', 'name', 'id')
    if sort == 'founded':
        return queryset.order_by('-date_created', 'short_name', 'id')

    return queryset.order_by('-total_rating', '-players_count', 'short_name', 'id')


def _active_club_filter_params(club_filters):
    params = {}
    for key in ('search', 'city', 'year'):
        value = club_filters[key]
        if value:
            params['q' if key == 'search' else key] = value

    if club_filters['sort'] != 'rating':
        params['sort'] = club_filters['sort']

    if club_filters.get('page_size') != DEFAULT_CLUBS_PAGE_SIZE:
        params[CLUBS_PAGE_SIZE_PARAM] = club_filters['page_size']

    return params


def _club_url(request, club_filters, page=None):
    params = _active_club_filter_params(club_filters)
    if page and page != 1:
        params['page'] = page

    query = urlencode(params)
    if not query:
        return request.path

    return '{}?{}'.format(request.path, query)


def _club_pagination_urls(request, club_filters, page_obj):
    return {
        'first': _club_url(request, club_filters, 1),
        'previous': _club_url(request, club_filters, page_obj.previous_page_number()) if page_obj.has_previous() else '#',
        'next': _club_url(request, club_filters, page_obj.next_page_number()) if page_obj.has_next() else '#',
        'last': _club_url(request, club_filters, page_obj.paginator.num_pages),
        'pages': {
            page: _club_url(request, club_filters, page)
            for page in _pagination_pages(page_obj)
            if page != 'ellipsis'
        },
    }


def _club_reset_url(request, club_filters):
    if club_filters['page_size'] == DEFAULT_CLUBS_PAGE_SIZE:
        return request.path

    return '{}?{}'.format(
        request.path,
        urlencode({CLUBS_PAGE_SIZE_PARAM: club_filters['page_size']}),
    )


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


def _club_pagination_summary(page_obj):
    if page_obj.paginator.count == 0:
        return _("Showing 0 of 0 clubs")

    return (
        _("Showing _START_ to _END_ of _TOTAL_ clubs")
        .replace('_START_', str(page_obj.start_index()))
        .replace('_END_', str(page_obj.end_index()))
        .replace('_TOTAL_', str(page_obj.paginator.count))
    )


def club(request, id):
    club_queryset = Club.objects.select_related('city', 'president')
    if not (request.user.is_authenticated and request.user.is_staff):
        club_queryset = club_queryset.filter(is_active=True)

    club = get_object_or_404(club_queryset, pk=id)
    players = (
        Player.objects
        .filter(current_club=club)
        .select_related('current_club')
        .order_by('-current_rating', 'surname', 'name')
    )
    rated_players = (
        players
        .filter(is_licence_active=True)
        .exclude(licence_number__isnull=True)
        .exclude(licence_number='')
    )

    rating_field = 'current_rating'
    rating_power_field = 'current_power'
    licence_filter = 'licence'

    rating_stats = rated_players.aggregate(
        total_rating=Sum('current_rating'),
        average_rating=Avg('current_rating'),
        average_power=Avg('current_power'),
        candidates_count=Count('id', filter=Q(sport_title='candidate')),
    )
    total_rating = rating_stats['total_rating'] or 0
    club_rank = (
        Club.objects
        .filter(is_active=True)
        .annotate(total_rating=Sum('player__current_rating', filter=RATED_CLUB_PLAYER_FILTER))
        .filter(total_rating__gt=total_rating)
        .count()
        + 1
    )
    national_team_players_count = (
        PlayerNational_teamMembership.objects
        .filter(player__current_club=club)
        .values('player_id')
        .distinct()
        .count()
    )
    club_stats = {
        'players_count': players.count(),
        'total_rating': total_rating,
        'average_rating': rating_stats['average_rating'] or 0,
        'average_power': rating_stats['average_power'] or 0,
        'club_rank': club_rank,
        'national_team_players_count': national_team_players_count,
        'candidates_count': rating_stats['candidates_count'] or 0,
    }

    return render(request, 'clubs/club.html', {
        'club': club,
        'club_stats': club_stats,
        'rating_field': rating_field,
        'rating_power_field': rating_power_field,
        'rating_filters': rating_field + "," + str(licence_filter),
        'players': players
    })
