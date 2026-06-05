from django.utils.translation import gettext_lazy as _

from federation.models.national_teams import National_team, PlayerNational_teamMembership
from federation.models.player import Player


ARBITER_SHORT_LABELS = {
    'junior': 'ЮСА',
    'arbiter': 'АФП',
    'club': 'CA II',
    'regional': 'CA I',
    'national': 'CA H',
    'euro': 'CEP',
    'fipjp': 'FIPJP',
}

COACH_SHORT_LABELS = {
    'A': 'A',
    'I1': 'I1',
    'I2': 'I2',
    'I3': 'I3',
    'I4': 'I4',
    'E1': 'E1',
    'E2': 'E2',
    'E3': 'E3',
    'E4': 'E4',
}

SPORT_TITLE_SHORT_LABELS = {
    'candidate': 'КМСУ',
    'master': 'МСУ',
    'master_sport': 'МСМК',
    'honored_master_sport': 'ЗМСУ',
}

NATIONAL_TEAM_POSITION_SHORT_LABELS = {
    'player': 'ГР',
    'coach': 'ТР',
    'main_coach': 'ГТ',
    'capitan': 'К',
    'selection': 'ОС',
}

ROUTE_CONFIG = {
    'arbiters': {
        'page_title': _('Arbiters'),
        'page_subtitle': _('Registry of arbiters of the Petanque Federation of Ukraine'),
        'sidebar_title': _('Arbiters'),
        'icon_class': 'bi-patch-check-fill',
    },
    'coaches': {
        'page_title': _('Coaches'),
        'page_subtitle': _('Registry of coaches and instructors of the Petanque Federation of Ukraine'),
        'sidebar_title': _('Coaches'),
        'icon_class': 'bi-person-badge',
    },
    'sport_titles': {
        'page_title': _('Sports titles'),
        'page_subtitle': _('Players with sports titles'),
        'sidebar_title': _('Titles'),
        'icon_class': 'bi-award-fill',
    },
    'national_teams': {
        'page_title': _('National Teams of Ukraine'),
        'page_subtitle': _('Players of the Ukrainian national petanque team'),
        'sidebar_title': _('National teams'),
        'icon_class': 'bi-flag-fill',
    },
    'departments': {
        'page_title': _('Structure'),
        'page_subtitle': _('Ukrainian Petanque Federation'),
        'sidebar_title': _('Structure'),
        'icon_class': 'bi-briefcase-fill',
    },
}


def title_registry_context(route_type, groups, active_group_key=None):
    return {
        'title_registry': {
            **ROUTE_CONFIG[route_type],
            'route_type': route_type,
            'groups': _mark_active_group(groups, active_group_key),
        },
        'page_title': ROUTE_CONFIG[route_type]['page_title'],
    }


def player_choice_groups(choices, field_name, short_labels, icon_class):
    groups = []

    for category_key, category_label in choices:
        players = list(
            Player.objects
            .filter(**{field_name: category_key})
            .select_related('current_club')
            .order_by('surname', 'name', 'licence_number')
        )

        if not players:
            continue

        label = str(category_label)
        short_label = short_labels.get(category_key, label[:4])

        groups.append({
            'key': category_key,
            'label': label,
            'short_label': short_label,
            'items': [
                {
                    'player': player,
                    'title_short': short_label,
                    'title_label': label,
                    'title_icon_class': icon_class,
                }
                for player in players
            ],
        })

    return groups


def national_team_groups():
    groups = []

    for team in National_team.objects.all().order_by('name'):
        memberships = list(
            PlayerNational_teamMembership.objects
            .filter(team=team, player__isnull=False)
            .select_related('player', 'player__current_club')
            .order_by('player__surname', 'player__name')
        )

        if not memberships:
            continue

        label = team.name or _('National team players')
        group_short_label = _short_label_from_text(label, 'ЗБ')

        groups.append({
            'key': f'team-{team.pk}',
            'label': label,
            'short_label': group_short_label,
            'items': [
                {
                    'player': membership.player,
                    'title_short': NATIONAL_TEAM_POSITION_SHORT_LABELS.get(
                        membership.position,
                        group_short_label,
                    ),
                    'title_label': membership.get_position_display(),
                    'title_icon_class': ROUTE_CONFIG['national_teams']['icon_class'],
                }
                for membership in memberships
            ],
        })

    return groups


def _mark_active_group(groups, active_group_key=None):
    active_key = active_group_key

    if active_key and not any(group['key'] == active_key for group in groups):
        active_key = None

    if not active_key and groups:
        active_key = groups[0]['key']

    for group in groups:
        players_count = len(group['items'])
        group['players_count'] = players_count
        group['players_count_label'] = _players_count_label(players_count)
        group['is_active'] = group['key'] == active_key

    return groups


def _players_count_label(count):
    if count % 10 == 1 and count % 100 != 11:
        suffix = 'особа'
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        suffix = 'особи'
    else:
        suffix = 'осіб'

    return f'{count} {suffix}'


def _short_label_from_text(text, fallback):
    words = [
        word.strip('.,()[]{}').upper()
        for word in str(text).split()
        if word.strip('.,()[]{}')
    ]
    initials = ''.join(word[0] for word in words[:3] if word)

    if initials:
        return initials

    return fallback
