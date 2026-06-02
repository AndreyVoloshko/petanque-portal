from django.shortcuts import render, redirect
from django.http import JsonResponse
from federation.models.player import Player
from federation.models.team import PlayerTeamMembership
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models import Prefetch
from django.db.models import Q
import csv
from transliterate import translit
from django.http import HttpResponse
from django.conf import settings
from django.urls import reverse
from django.utils import formats, timezone
from django.utils.html import escape
from django.http import HttpResponseRedirect
from django.utils.translation import get_language, gettext_lazy as _, ngettext
from urllib.parse import urlencode
import logging, json, re
from django.views.decorators.csrf import csrf_exempt
from federation.permissions import can_create_tournament
from federation.utils.tournament_names import get_tournament_card_metadata


_SPACES_RE = re.compile(r'\s+')
DEFAULT_TOURNAMENTS_PAGE_SIZE = 50
TABLET_TOURNAMENTS_PAGE_SIZE = 30
MOBILE_TOURNAMENTS_PAGE_SIZE = 25
TOURNAMENTS_PAGE_SIZE_PARAM = 'per_page'
TOURNAMENTS_PAGE_SIZE_OPTIONS = {
    DEFAULT_TOURNAMENTS_PAGE_SIZE,
    TABLET_TOURNAMENTS_PAGE_SIZE,
    MOBILE_TOURNAMENTS_PAGE_SIZE,
    5,
}
UK_FULL_MONTHS_GENITIVE = {
    1: 'Січня',
    2: 'Лютого',
    3: 'Березня',
    4: 'Квітня',
    5: 'Травня',
    6: 'Червня',
    7: 'Липня',
    8: 'Серпня',
    9: 'Вересня',
    10: 'Жовтня',
    11: 'Листопада',
    12: 'Грудня',
}


def _current_language():
    language = get_language() or 'uk'
    return 'uk' if language.startswith('uk') else 'en'


def tournaments(request, date_filter=None, type_filter=None):
    filters = _get_tournament_filters(request, date_filter, type_filter)
    queryset = _get_tournaments_queryset(filters)
    filter_options = _get_tournament_filter_options(queryset)
    rows = [_build_tournament_row(tournament) for tournament in queryset]
    rows = [row for row in rows if _row_matches_filters(row, filters)]

    paginator = Paginator(rows, filters['page_size'])
    page_obj = paginator.get_page(request.GET.get('page'))
    page_rows = page_obj.object_list
    active_filters = _active_filter_params(filters)

    page_title = _("Competitions")
    return render(request, 'tournaments/tournaments.html', {
        'page_title': page_title,
        'filters': filters,
        'period_tabs': _get_period_tabs(filters),
        'format_options': FORMAT_OPTIONS,
        'category_options': CATEGORY_OPTIONS,
        'place_options': filter_options['places'],
        'rows': page_rows,
        'show_strength': True,
        'page_obj': page_obj,
        'page_size': filters['page_size'],
        'pagination_pages': _pagination_pages(page_obj),
        'pagination_summary': _pagination_summary(page_obj),
        'pagination_urls': _pagination_urls(filters, page_obj),
        'sort_state': _get_sort_state(filters),
        'active_filters': active_filters,
        'has_active_secondary_filters': _has_active_secondary_filters(filters),
        'reset_url': _reset_url(filters),
        'can_create_tournament': can_create_tournament(request.user),
        'admin_add_url': reverse('admin:federation_tournament_add'),
        'empty_state': _empty_state(filters),
    })


PERIODS = ('future', 'ongoing', 'past')
PERIOD_ROUTE_ALIASES = {
    'future': 'future',
    'current': 'ongoing',
    'ongoing': 'ongoing',
    'past': 'past',
}
TYPE_ROUTE_ALIASES = {
    'rating': 'rating',
    'non_rating': 'non_rating',
    'away': 'all',
}
FORMAT_OPTIONS = (
    ('tete', _('Тет-а-тет')),
    ('doublets', _('Дуплети')),
    ('triplets', _('Триплети')),
    ('shooting', _('Тир')),
    ('clubs', _('Клуби')),
    ('supermelee', _('Супермеле')),
)
CATEGORY_OPTIONS = (
    ('men', _('Чоловіки')),
    ('women', _('Жінки')),
    ('mixed', _('Змішані')),
    ('juniors', _('Юніори')),
    ('veterans', _('Ветерани 55+')),
    ('open', _('Відкриті')),
)
STATUS_LABELS = {
    'registration_open': _('Реєстрація відкрита'),
    'registration_closed': _('Реєстрація закрита'),
    'registration_unavailable': _('Реєстрація недоступна'),
    'ongoing': _('Триває'),
    'finished': _('Завершено'),
    'cancelled': _('Скасовано'),
}
COUNTRY_LABELS = {
    'AT': {'uk': 'Австрія', 'en': 'Austria'},
    'BE': {'uk': 'Бельгія', 'en': 'Belgium'},
    'BG': {'uk': 'Болгарія', 'en': 'Bulgaria'},
    'CZ': {'uk': 'Чехія', 'en': 'Czechia'},
    'ES': {'uk': 'Іспанія', 'en': 'Spain'},
    'FR': {'uk': 'Франція', 'en': 'France'},
    'GR': {'uk': 'Греція', 'en': 'Greece'},
    'HR': {'uk': 'Хорватія', 'en': 'Croatia'},
    'HU': {'uk': 'Угорщина', 'en': 'Hungary'},
    'IL': {'uk': 'Ізраїль', 'en': 'Israel'},
    'LV': {'uk': 'Латвія', 'en': 'Latvia'},
    'MY': {'uk': 'Малайзія', 'en': 'Malaysia'},
    'NL': {'uk': 'Нідерланди', 'en': 'Netherlands'},
    'PL': {'uk': 'Польща', 'en': 'Poland'},
    'SK': {'uk': 'Словаччина', 'en': 'Slovakia'},
    'UA': {'uk': 'Україна', 'en': 'Ukraine'},
}
COUNTRY_ALIASES = {
    'австрія': 'AT',
    'austria': 'AT',
    'бельгія': 'BE',
    'belgium': 'BE',
    'болгарія': 'BG',
    'bulgaria': 'BG',
    'croatia': 'HR',
    'czech republic': 'CZ',
    'czechia': 'CZ',
    'греція': 'GR',
    'greece': 'GR',
    'hungary': 'HU',
    'іспанія': 'ES',
    'ізраїль': 'IL',
    'israel': 'IL',
    'latvia': 'LV',
    'латвія': 'LV',
    'малайзія': 'MY',
    'malaysia': 'MY',
    'netherlands': 'NL',
    'нідерланди': 'NL',
    'poland': 'PL',
    'польща': 'PL',
    'slovakia': 'SK',
    'словаччина': 'SK',
    'словаччнина': 'SK',
    'spain': 'ES',
    'україна': 'UA',
    'угорщина': 'HU',
    'ukraine': 'UA',
    'france': 'FR',
    'франція': 'FR',
    'хорватія': 'HR',
    'чехія': 'CZ',
}
PERIOD_LABELS = {
    'future': _('Майбутні'),
    'ongoing': _('Теперішні'),
    'past': _('Минулі'),
}
PERIOD_ICONS = {
    'future': 'bi-calendar-event',
    'ongoing': 'bi-shield-check',
    'past': 'bi-clock-history',
}
FORMAT_LABEL_TO_KEY = {
    'Тет-а-тет': 'tete',
    'Tete-a-tete': 'tete',
    'Дуплети': 'doublets',
    'Doubles': 'doublets',
    'Триплети': 'triplets',
    'Triples': 'triplets',
    'Тир': 'shooting',
    'Shooting': 'shooting',
    'Клуби': 'clubs',
    'Clubs': 'clubs',
    'Супер-меле': 'supermelee',
    'Супермеле': 'supermelee',
    'Super melee': 'supermelee',
}


def _get_tournament_filters(request, date_filter, type_filter):
    route_period = PERIOD_ROUTE_ALIASES.get(date_filter or '', 'future')
    route_rating_type = TYPE_ROUTE_ALIASES.get(type_filter or '', 'all')
    period = request.GET.get('period') or route_period
    rating_type = request.GET.get('type') or route_rating_type

    if period not in PERIODS:
        period = 'future'

    if rating_type not in ('all', 'rating', 'non_rating'):
        rating_type = 'all'

    sort = request.GET.get('sort') or _default_sort(period)
    if sort not in ('date_asc', 'date_desc'):
        sort = _default_sort(period)

    foreign = _truthy(request.GET.get('foreign'))
    if type_filter == 'away' and 'foreign' not in request.GET:
        foreign = True

    return {
        'period': period,
        'rating_type': rating_type,
        'foreign': foreign,
        'search': request.GET.get('q', '').strip(),
        'format': request.GET.get('format', '').strip(),
        'category': request.GET.get('category', '').strip(),
        'place': request.GET.get('place', '').strip(),
        'club': request.GET.get('club', '').strip(),
        'sort': sort,
        'page_size': _get_page_size(request),
    }


def _get_page_size(request):
    try:
        page_size = int(request.GET.get(TOURNAMENTS_PAGE_SIZE_PARAM, DEFAULT_TOURNAMENTS_PAGE_SIZE))
    except (TypeError, ValueError):
        return DEFAULT_TOURNAMENTS_PAGE_SIZE

    if page_size in TOURNAMENTS_PAGE_SIZE_OPTIONS:
        return page_size

    return DEFAULT_TOURNAMENTS_PAGE_SIZE


def _truthy(value):
    return str(value or '').lower() in ('1', 'true', 'yes', 'on')


def _get_tournaments_queryset(filters):
    queryset = (
        Tournament.objects
        .select_related('organizer_club')
        .annotate(actual_teams_count=Count('teamtournamentmembership', distinct=True))
    )
    queryset = _apply_rating_filter(queryset, filters['rating_type'])
    queryset = _apply_foreign_filter(queryset, filters['foreign'])
    queryset = _apply_period_filter(queryset, filters['period'])

    if filters['sort'] == 'date_desc':
        return queryset.order_by('-start_date', '-id')

    return queryset.order_by('start_date', 'id')


def _default_sort(period):
    if period == 'past':
        return 'date_desc'
    return 'date_asc'


def _apply_rating_filter(queryset, rating_type):
    if rating_type == 'rating':
        return queryset.filter(is_goes_to_rating=True)

    if rating_type == 'non_rating':
        return queryset.filter(is_goes_to_rating=False)

    return queryset


def _apply_foreign_filter(queryset, foreign):
    if not foreign:
        return queryset

    current_country = getattr(settings, 'CURRENT_COUNTRY', None)
    if current_country:
        return queryset.filter(Q(category='away') | ~Q(country=current_country))

    return queryset.filter(category='away')


def _apply_period_filter(queryset, period):
    today = timezone.localdate()

    if period == 'past':
        return queryset.filter(
            Q(end_date__lt=today) |
            Q(end_date__isnull=True, start_date__lt=today)
        )

    if period == 'ongoing':
        return queryset.filter(
            Q(start_date__lte=today, end_date__gte=today) |
            Q(start_date=today, end_date__isnull=True)
        )

    return queryset.filter(start_date__gt=today)


def _get_tournament_filter_options(queryset):
    places = sorted({place for place in queryset.values_list('place', flat=True) if place})

    return {
        'places': places,
    }


def _build_tournament_row(tournament):
    metadata = get_tournament_card_metadata(tournament)
    format_label = _display_format_label(metadata.get('format'))
    audience_tags = [_display_category_label(tag) for tag in metadata.get('audience_tags', [])]
    status = _tournament_status_data(tournament)
    country_data = _display_country_data(tournament)
    place_label = _place_label(tournament, country_data)
    format_labels = metadata.get('format_tags') or [metadata.get('format')]
    format_labels = [label for label in format_labels if label]
    format_keys = [FORMAT_LABEL_TO_KEY.get(label, '') for label in format_labels]

    return {
        'tournament': tournament,
        'title': metadata.get('name') or tournament.get_name(),
        'full_title': tournament.name,
        'date_label': _date_full_month_label(tournament.start_date),
        'weekday_label': formats.date_format(tournament.start_date, 'l') if tournament.start_date else '',
        'teams_count_label': _registered_count_label(
            _resolved_tournament_teams_count(tournament),
            _is_single_player_format(tournament, format_keys),
        ),
        'format_label': format_label,
        'format_labels': format_labels,
        'format_keys': format_keys,
        'audience_tags': audience_tags,
        'category_keys': _category_keys(audience_tags),
        'openness_label': _openness_label(tournament),
        'openness_key': _openness_key(tournament),
        'place_label': place_label,
        'place_key': tournament.place or '',
        'country_name': country_data['name'],
        'country_code': country_data['code'].lower(),
        'is_foreign': _is_foreign_tournament(tournament),
        'organizer_label': _organizer_label(tournament),
        'organizer_url': _organizer_url(tournament),
        'status': status,
        'detail_url': reverse('tournament', args=[tournament.pk]),
        'registration_url': reverse('register_team', args=[tournament.pk]),
        'protocol_url': reverse('tournament_protocol', args=[tournament.pk]),
        'show_results_action': tournament.is_processing_closed(),
    }


def _date_full_month_label(value):
    if not value:
        return ''

    if _current_language() == 'uk':
        return '{} {} {}'.format(
            value.day,
            UK_FULL_MONTHS_GENITIVE[value.month],
            value.year,
        )

    return formats.date_format(value, 'j F Y')


def _display_format_label(format_label):
    if format_label in ('Супер-меле', 'Super melee'):
        return _('Супермеле') if format_label == 'Супер-меле' else format_label
    return format_label or ''


def _registered_count_label(count, is_single_player_format=False):
    count = int(count or 0)
    if is_single_player_format:
        if _current_language() == 'en':
            return ngettext('%(count)d player', '%(count)d players', count) % {'count': count}
        return '{} {}'.format(count, _uk_plural(count, 'гравець', 'гравці', 'гравців'))

    if _current_language() == 'en':
        return ngettext('%(count)d team', '%(count)d teams', count) % {'count': count}

    return '{} {}'.format(count, _uk_plural(count, 'команда', 'команди', 'команд'))


def _resolved_tournament_teams_count(tournament):
    if tournament.total_number_of_teams and tournament.total_number_of_teams > 0:
        return tournament.total_number_of_teams

    annotated_count = getattr(tournament, 'actual_teams_count', None)
    if annotated_count is not None:
        return annotated_count

    return tournament.get_teams_count()


def _uk_plural(count, singular, few, many):
    if count % 10 == 1 and count % 100 != 11:
        return singular
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return few
    return many


def _is_single_player_format(tournament, format_keys):
    if 'tete' in format_keys:
        return True

    try:
        players_min = int(tournament.number_of_players_in_team_min or 0)
        players_max = int(tournament.number_of_players_in_team_max or 0)
    except (TypeError, ValueError):
        return False

    return players_min == 1 and players_max == 1


def _display_category_label(label):
    if label in ('Мікст', 'Mix', 'Mixed'):
        return _('Змішані') if _current_language() == 'uk' else 'Mixed'
    if label in ('Ветерани', 'Veterans'):
        return _('Ветерани 55+')
    return label


def _category_keys(tags):
    if not tags:
        return ['open']

    keys = set()
    for tag in tags:
        normalized = str(tag).lower()
        if 'чолов' in normalized or normalized in ('men', 'male'):
            keys.add('men')
        if 'жін' in normalized or normalized in ('women', 'female'):
            keys.add('women')
        if 'змішан' in normalized or 'мікст' in normalized or normalized in ('mixed', 'mix'):
            keys.add('mixed')
        if (
            'юніор' in normalized or
            'молод' in normalized or
            'юнак' in normalized or
            normalized in ('juniors', 'junior', 'youth', 'cadets', 'cadet')
        ):
            keys.add('juniors')
        if 'ветеран' in normalized or normalized in ('veterans', 'veteran', 'veterans 55+'):
            keys.add('veterans')

    return sorted(keys) or ['open']


def _openness_label(tournament):
    if _openness_key(tournament) == 'closed':
        return _('Закритий')
    return _('Відкритий')


def _openness_key(tournament):
    if tournament.category == 'fpu':
        return 'closed'
    return 'open'


def _country_name(tournament):
    country = getattr(tournament, 'country', None)
    if not country:
        return ''
    return str(getattr(country, 'name', '') or '')


def _country_code(tournament):
    country = getattr(tournament, 'country', None)
    return str(getattr(country, 'code', '') or country or '')


def _localized_country_name(country_code):
    labels = COUNTRY_LABELS.get(country_code, {})
    return labels.get(_current_language()) or labels.get('uk') or ''


def _display_country_data(tournament):
    place_country_code = _infer_country_code_from_place(tournament.place)
    code = place_country_code or _country_code(tournament).upper()
    name = _localized_country_name(code) or _country_name(tournament)
    return {
        'code': code,
        'name': name,
        'inferred_from_place': bool(place_country_code),
    }


def _infer_country_code_from_place(place):
    for part in _place_parts(place):
        code = COUNTRY_ALIASES.get(part)
        if code:
            return code
    return ''


def _place_parts(place):
    normalized = str(place or '').lower()
    return [
        _clean_place_part(part)
        for part in normalized.split(',')
        if _clean_place_part(part)
    ]


def _clean_place_part(part):
    return _SPACES_RE.sub(' ', str(part or '').strip().lower())


def _place_label(tournament, country_data):
    place = tournament.place or ''
    country_name = country_data['name']
    country_code = country_data['code']
    current_country = getattr(settings, 'CURRENT_COUNTRY', None)

    if country_data['inferred_from_place'] and len(_place_parts(place)) == 1:
        return country_name

    if _place_contains_country(place, country_code, country_name):
        return place

    if (
        _is_foreign_tournament(tournament) and
        country_name and
        country_code != current_country
    ):
        return ', '.join(part for part in (place, country_name) if part)

    return place or country_name or '—'


def _place_contains_country(place, country_code, country_name):
    parts = _place_parts(place)
    if not parts:
        return False

    aliases = {alias for alias, code in COUNTRY_ALIASES.items() if code == country_code}
    for label in COUNTRY_LABELS.get(country_code, {}).values():
        aliases.add(_clean_place_part(label))

    return any(part in aliases for part in parts)


def _is_foreign_tournament(tournament):
    if tournament.category == 'away':
        return True

    current_country = getattr(settings, 'CURRENT_COUNTRY', None)
    country_code = _country_code(tournament)
    return bool(country_code and current_country and country_code != current_country)


def _organizer_label(tournament):
    if not tournament.organizer_club:
        return _('Без клубу')
    return tournament.organizer_club.short_name or tournament.organizer_club.name


def _organizer_url(tournament):
    if not tournament.organizer_club:
        return ''
    return reverse('club', args=[tournament.organizer_club.pk])


def _tournament_status_data(tournament):
    status_key = _tournament_status_key(tournament)
    return {
        'key': status_key,
        'label': STATUS_LABELS[status_key],
        'note': _tournament_status_note(tournament, status_key),
    }


def _tournament_status_key(tournament):
    if _is_cancelled(tournament):
        return 'cancelled'

    today = timezone.localdate()
    start_date = tournament.start_date
    end_date = tournament.end_date

    if start_date and start_date <= today:
        if end_date and end_date >= today:
            return 'ongoing'
        if not end_date and start_date == today:
            return 'ongoing'

    if tournament.is_processing_closed() or _is_finished_by_dates(tournament, today):
        return 'finished'

    if tournament.date_registration_stop:
        if tournament.date_registration_stop >= timezone.now():
            return 'registration_open'
        return 'registration_closed'

    return 'registration_unavailable'


def _is_finished_by_dates(tournament, today):
    if tournament.end_date:
        return tournament.end_date < today
    return bool(tournament.start_date and tournament.start_date < today)


def _is_cancelled(tournament):
    if getattr(tournament, 'is_cancelled', False):
        return True

    try:
        meta = json.loads(tournament.meta or '{}')
    except (TypeError, ValueError):
        return False

    return bool(
        meta.get('cancelled') or
        meta.get('is_cancelled') or
        meta.get('status') == 'cancelled'
    )


def _tournament_status_note(tournament, status_key):
    if status_key in ('registration_open', 'registration_closed') and tournament.date_registration_stop:
        date_str = formats.date_format(tournament.date_registration_stop, 'SHORT_DATE_FORMAT')
        time_str = formats.time_format(tournament.date_registration_stop, 'H:i')
        return '{} {} {}'.format(_('до'), date_str, time_str)

    if status_key == 'ongoing':
        return _date_range_label(tournament)

    if status_key == 'finished' and tournament.is_processing_closed():
        return _('результати доступні')

    return ''


def _date_range_label(tournament):
    if not tournament.start_date:
        return ''

    if tournament.end_date and tournament.end_date != tournament.start_date:
        start = formats.date_format(tournament.start_date, 'SHORT_DATE_FORMAT')
        end = formats.date_format(tournament.end_date, 'SHORT_DATE_FORMAT')
        return '{} — {}'.format(start, end)

    return formats.date_format(tournament.start_date, 'SHORT_DATE_FORMAT')


def _row_matches_filters(row, filters):
    if filters['search']:
        tokens = filters['search'].lower().split()
        haystack = ' '.join([
            str(row['title']),
            str(row['format_label']),
            str(row['place_label']),
            str(row['country_name']),
            str(row['organizer_label']),
            str(row['tournament'].get_display_name()),
        ]).lower()
        if not all(token in haystack for token in tokens):
            return False

    if filters['format'] and filters['format'] not in row['format_keys']:
        return False

    if filters['category'] and filters['category'] not in row['category_keys']:
        return False

    if filters['place'] and row['place_key'] != filters['place']:
        return False

    if filters['club'] and str(row['tournament'].organizer_club_id or '') != filters['club']:
        return False

    return True


def _get_period_tabs(filters):
    tabs = []
    for period in PERIODS:
        tab_filters = dict(filters)
        tab_filters['period'] = period
        tab_filters['sort'] = _default_sort(period)
        tabs.append({
            'key': period,
            'label': PERIOD_LABELS[period],
            'icon': PERIOD_ICONS[period],
            'count': _count_tournaments_for_filters(tab_filters),
            'active': filters['period'] == period,
            'url': _url_for_filters(tab_filters),
        })

    return tabs


def _count_tournaments_for_filters(filters):
    queryset = _get_tournaments_queryset(filters)
    rows = [_build_tournament_row(tournament) for tournament in queryset]
    return sum(1 for row in rows if _row_matches_filters(row, filters))


def _active_filter_params(filters):
    params = {
        'period': filters['period'],
    }

    if filters['rating_type'] != 'all':
        params['type'] = filters['rating_type']

    if filters['foreign']:
        params['foreign'] = '1'

    for key in ('search', 'format', 'category', 'place', 'club'):
        value = filters[key]
        if value:
            params['q' if key == 'search' else key] = value

    if filters.get('sort') and filters['sort'] != _default_sort(filters['period']):
        params['sort'] = filters['sort']

    if filters.get('page_size') and filters['page_size'] != DEFAULT_TOURNAMENTS_PAGE_SIZE:
        params[TOURNAMENTS_PAGE_SIZE_PARAM] = filters['page_size']

    return params


def _has_active_secondary_filters(filters):
    return (
        filters['rating_type'] != 'all' or
        filters['foreign'] or
        any(filters[key] for key in ('search', 'format', 'category', 'place', 'club'))
    )


def _url_for_filters(filters, page=None):
    params = _active_filter_params(filters)
    if page and page != 1:
        params['page'] = page

    query = urlencode(params)
    if not query:
        return reverse('tournaments')

    return '{}?{}'.format(reverse('tournaments'), query)


def _reset_url(filters):
    if filters.get('page_size') == DEFAULT_TOURNAMENTS_PAGE_SIZE:
        return reverse('tournaments')

    return '{}?{}'.format(
        reverse('tournaments'),
        urlencode({TOURNAMENTS_PAGE_SIZE_PARAM: filters['page_size']}),
    )


def _get_sort_state(filters):
    direction = 'desc' if filters['sort'] == 'date_desc' else 'asc'
    next_filters = dict(filters)
    next_filters['sort'] = 'date_asc' if direction == 'desc' else 'date_desc'

    return {
        'date_direction': direction,
        'date_url': _url_for_filters(next_filters),
    }


def _pagination_pages(page_obj):
    paginator = page_obj.paginator
    current = page_obj.number
    pages = []

    for number in paginator.page_range:
        if number == 1 or number == paginator.num_pages or abs(number - current) <= 1:
            pages.append(number)
        elif pages and pages[-1] != 'ellipsis':
            pages.append('ellipsis')

    return pages


def _pagination_urls(filters, page_obj):
    urls = {
        'first': _url_for_filters(filters, 1),
        'last': _url_for_filters(filters, page_obj.paginator.num_pages),
        'previous': '',
        'next': '',
        'pages': {},
    }

    if page_obj.has_previous():
        urls['previous'] = _url_for_filters(filters, page_obj.previous_page_number())

    if page_obj.has_next():
        urls['next'] = _url_for_filters(filters, page_obj.next_page_number())

    for page in _pagination_pages(page_obj):
        if page != 'ellipsis':
            urls['pages'][page] = _url_for_filters(filters, page)

    return urls


def _pagination_summary(page_obj):
    total = page_obj.paginator.count
    if total == 0:
        return _('Показано 0 з 0 турнірів')

    return _('Показано %(start)s–%(end)s з %(total)s турнірів') % {
        'start': page_obj.start_index(),
        'end': page_obj.end_index(),
        'total': total,
    }


def _empty_state(filters):
    if _has_active_secondary_filters(filters):
        return {
            'title': _('Змагання не знайдено'),
            'description': _('Спробуйте змінити фільтри або очистити пошук.'),
        }

    if filters['period'] == 'future':
        return {
            'title': _('Наразі немає майбутніх турнірів'),
            'description': _('Перегляньте минулі змагання або змініть фільтри.'),
        }

    if filters['period'] == 'ongoing':
        return {
            'title': _('Зараз немає турнірів, що тривають'),
            'description': _('Перегляньте майбутні або минулі змагання.'),
        }

    return {
        'title': _('Минулі турніри не знайдено'),
        'description': _('Спробуйте змінити фільтри.'),
    }

@csrf_exempt
def tournament(request, id):
    current_user = request.user

    tournament = get_object_or_404(
        Tournament.objects.select_related(
            'organizer_club',
            'main_organizer',
            'main_organizer__user',
            'federation_delegat',
        ),
        pk=id,
    )

    if request.method == "POST":
        if 'meta' in request.POST:
            tournament.meta = request.POST['meta']
            tournament.save()
            return JsonResponse({'status': 'ok'}, safe=False)

        if 'tournament_notes_content' in request.POST and current_user.is_authenticated:
            if tournament.is_user_has_admin_access_to_tournament(current_user):
                tournament.final_notes = escape(request.POST['tournament_notes_content'])
                tournament.save()
                messages.success(request, _('Notes saved.'))
                return HttpResponseRedirect(request.path_info)

        if 'delete_team_id' in request.POST and current_user.is_authenticated:
            team = TeamTournamentMembership.objects.get(pk=request.POST['delete_team_id'])
            if team and team.is_user_has_admin_access_to_team(current_user):
                team.delete()
                messages.success(request, _('Team removed.'))
                return HttpResponseRedirect(request.path_info)

        if 'teams' in request.POST and current_user.is_authenticated:
            if tournament.is_user_has_admin_access_to_tournament(current_user):

                teams = json.loads(request.POST['teams'])

                for team in teams:
                    name_pieces = team['name'].split('-')
                    db_team = TeamTournamentMembership.objects.get(pk=name_pieces[0])

                    if db_team:

                        if not team['value']:
                            team['value'] = 0

                        if name_pieces[1] == 'min':
                            db_team.place_min = team['value']
                        elif name_pieces[1] == 'max':
                            db_team.place_max = team['value']
                        db_team.save()

                messages.success(request, _('Team places updated.'))
                return HttpResponseRedirect(request.path_info)

    arbiters = ArbiterTournamentMembership.objects.filter(tournament=tournament).select_related('arbiter')
    teams = (
        TeamTournamentMembership.objects
        .filter(tournament=tournament)
        .select_related('team', 'tournament', 'tournament__main_organizer', 'tournament__main_organizer__user')
        .prefetch_related(
            Prefetch(
                'team__players',
                queryset=Player.objects.select_related('current_club', 'user').order_by('surname', 'name'),
            ),
            Prefetch(
                'team__playerteammembership_set',
                queryset=PlayerTeamMembership.objects.filter(is_capitan=True).select_related('player'),
                to_attr='captain_memberships',
            ),
        )
    )

    return render(request, 'tournaments/tournament.html', {
        'tournament': tournament,
        'arbiters': arbiters,
        'teams': teams,
        'page_title': _("Competitions"),
        'current_user': current_user
    })


def tournament_teams_export(request, id):

    try:
        output_format = request.GET.get('format', 'html')
    except Exception:
        output_format = 'html'

    tournament = get_object_or_404(Tournament, pk=id)
    teams = TeamTournamentMembership.objects.filter(tournament=tournament).order_by('place_min')

    if output_format == 'csv':

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv;charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="'+str(tournament.pk)+'-teams.csv"'
        writer = csv.writer(response,
                            delimiter=';',
                            lineterminator='\n',
                            quoting=csv.QUOTE_MINIMAL,
                            dialect='excel'
                            )

        row = [tournament.number_of_players_in_team_min]
        writer.writerow(row)

        row = []

        for i in range(1, tournament.number_of_players_in_team_min + 1):
            row.append("LASTNAME" + str(i))
            row.append("FIRSTNAME" + str(i))
            row.append("GENDER" + str(i))
            row.append("CLUB" + str(i))

        row.append("NAME")
        row.append("SEED")
        row.append("STATUS")
        row.append("RANK")
        writer.writerow(_encode_row(row))

        for team in tournament.teams.all():
            row = []
            player_index = 0

            for player in team.players.all():
                if player_index >= tournament.number_of_players_in_team_min:
                    break

                player_index += 1

                club_name = ""
                if player.current_club is not None:
                    club_name = player.current_club.name

                if player is not None:
                    row.append(player.name)
                    row.append(player.surname)
                    row.append(player.gender)
                    row.append(club_name)
                else:
                    # empty player
                    row.append("")
                    row.append("")
                    row.append("")
                    row.append("")

            row.append(team.get_short_name())
            row.append("0") # seed
            row.append("") # status
            row.append("") # rank

            writer.writerow(_encode_row(row))

        return response

    elif output_format == 'json':
        def _player_brief(player):
            return {
                'id': player.pk,
                'name': player.name,
                'surname': player.surname,
                'second_name': player.second_name,
            }

        result = {
            'tournament': {
                'id': tournament.pk,
                'name': tournament.name,
                'display_name': tournament.get_display_name(),
                'meta': tournament.meta,
                'start_date': tournament.start_date,
                'start_time': tournament.start_time,
                'organizer_club': {'id': tournament.organizer_club.pk, 'name': tournament.organizer_club.name} if tournament.organizer_club else None,
                'main_organizer': _player_brief(tournament.main_organizer) if tournament.main_organizer else None,
                'federation_delegat': _player_brief(tournament.federation_delegat) if tournament.federation_delegat else None,
                'arbiters': [
                    {**_player_brief(m.arbiter), 'is_main_arbiter': m.is_main_arbiter}
                    for m in tournament.arbitertournamentmembership_set.select_related('arbiter').all()
                ],
            },
            'teams': []
        }

        for team in teams:
            current_team = {
                'id': team.team.pk,
                'power': team.power,
                'place_min': team.place_min,
                'place_max': team.place_max,
                'date_registration': team.date_registration,
                'rating_points': team.rating_points,
                'rating_power': team.rating_power,
                'power': team.power,
                'name': team.team.get_short_name(),
                'players': []
            }

            for player in team.team.players.all():
                club_name = ""
                club_id = None
                if player.current_club is not None:
                    club_name = player.current_club.name
                    club_id = player.current_club.pk

                current_team['players'].append({
                    'id': player.pk,
                    'name': player.name,
                    'surname': player.surname,
                    'second_name': player.second_name,
                    'club': club_name,
                    'club_id': club_id,
                    'sport_title': player.sport_title,
                })


            result['teams'].append(current_team)

        return JsonResponse(result)
    else:
        return render(request, 'tournaments/pure_teams_list.html', {
            'tournament': tournament,
            'teams': teams,
        })


def tournaments_calendar (request):
    return render(request, 'tournaments/calendar.html')


def tournament_protocol(request, id):
    tournament = get_object_or_404(Tournament, pk=id)

    if not tournament.is_processing_closed():
        return redirect('tournament', id=tournament.pk)

    # if tournament.country != settings.CURRENT_COUNTRY:
    #     return redirect('tournament', id=tournament.pk)

    arbiters = ArbiterTournamentMembership.objects.filter(tournament=tournament)
    teams = TeamTournamentMembership.objects.filter(tournament=tournament).order_by('place_min')

    players_count = 0
    for team in teams:
        players_count += team.team.players.count()

    return render(request, 'tournaments/tournament_protocol.html', {
        'tournament': tournament,
        'arbiters': arbiters,
        'teams_count': len(teams),
        'teams': teams[:4],
        'players_count': players_count
    })


def _encode_row(values):
    tmp = []
    replace_mapping = [
        ('і', 'и'), ('ї', 'йи'), ('ґ', 'г'), ('є', 'е'),
        ('І', 'И'), ('Ї', 'Йи'), ('Ґ', 'Г'), ('Є', 'Е')
    ]

    for item in values:
        item = str(item)
        for k, v in replace_mapping:
            item = item.replace(k, v)

        tmp.append(translit(item, 'ru', reversed=True).encode("utf-8").decode("utf-8"))
    return tmp
