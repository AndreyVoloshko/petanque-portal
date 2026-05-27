from django import template
from django.conf import settings
from decimal import Decimal, InvalidOperation
import os.path
from federation.models.team import Team
from federation.models.player import Player
from federation.models.record import Record
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from federation.models.national_teams import National_team, PlayerNational_teamMembership
from federation.models.department import PlayerDepartmentMembership
from datetime import date
from django.utils import formats
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _
from federation.helpers.general import get_model
from federation.utils.tournament_names import get_tournament_card_metadata, get_tournament_display_name
import json

register = template.Library()


@register.filter(name='comma_concat')
def comma_concat(str1, str2):
    return str(str1)+","+str(str2)


@register.filter(name='user_avatar')
def user_avatar(user):
    return settings.MEDIA_URL + str(user.avatar)


@register.filter(name='user_field')
def user_field(value):
    if value == None:
        return ''
    return value


@register.filter(name='format_date')
def format_date(value):
    return value.strftime('%d.%m.%Y')


@register.filter(name='format_datetime')
def format_datetime(value):
    return value.strftime('%d.%m.%Y %H:%M')


@register.filter(name='get_year')
def get_year(value):
    return value.strftime('%Y')


@register.filter(name='country_icon')
def country_icon(country):
    if not country.code:
        return '<span class="badge bg-danger">' + _('Country not specified') + '</span>'
    return '''
        ''' + str(country.name) + '''&nbsp;<i class="flag-icon flag-icon-'''+country.code+'''"></i>
    '''

@register.filter(name='country_flag')
def country_flag(country):
    return '''
        &nbsp;<i data-toggle="tooltip" data-placement="top" title="" data-original-title="''' + str(country.name) + '''" class="flag-icon flag-icon-'''+country.code+'''"></i>
    '''


@register.filter(name='club_logo')
def club_logo(club, additional_class=''):
    url = settings.MEDIA_ROOT + str(club.logo)

    if not club.logo:
        url = settings.STATIC_URL + 'default.png'

    return '''
        <a href="/club/''' + str(club.id) + '''">
            <div class="logo-container club overflow-hidden border ''' + additional_class + '''">
                <img src=''' + url + ''' class="img-fluid" />
            </div>
        </a>
    '''


@register.filter(name='user_avatar')
def user_avatar(user, additional_class=''):
    # Установка URL-аватара
    if hasattr(user, 'avatar') and user.avatar:
        url = f"{settings.MEDIA_URL}{user.avatar}"
    else:
        url = f"{settings.STATIC_URL}default.png"

    user_id = getattr(user, 'id', '')

    return format_html(
        '''
        <a href="/player/{user_id}" class="d-inline-block">
            <div class="rounded-circle overflow-hidden border {additional_class} logo-container">
                <img src="{url}?v={cache_bust}" class="img-fluid" style="width: 100%; height: 100%; object-fit: cover;">
            </div>
        </a>
        ''',
        user_id=user_id,
        additional_class=additional_class,
        url=url,
        cache_bust=user.avatar and user.avatar.url or 'nocache'
    )


@register.filter(name='user_profile_link')
def user_profile_link(user, is_link=True):
    sport_title = ""
    if user.sport_title:
        sport_title = ' <span class="text-secondary" data-bs-toggle="tooltip" data-bs-original-title="'+  user.get_sport_title_display() +'"><i class="bi bi-award"></i></span>'
    
    if not is_link:
        return user.get_name() + sport_title
    return '<a class="font-weight-normal" href="/player/' + str(user.id) + '">' + user.get_name() + '</a>' + sport_title


@register.filter(name="get_number_of_players")
def get_number_of_players (club):
    number_of_players = Player.objects.filter(current_club=club).exclude(is_licence_active=False).count()
    return number_of_players


@register.filter(name="get_club_rating_points")
def get_club_rating_points (club):
    players = Player.objects.filter(current_club=club).exclude(is_licence_active=False)
    points = 0

    for player in players:
        points += player.current_rating

    return round(points, 2)


@register.filter(name="get_club_avg_rating_points")
def get_club_avg_rating_points (club):
    players = Player.objects.filter(current_club=club).exclude(is_licence_active=False)

    players_count = players.count()

    if players_count <= 0:
        return 0

    points = 0

    for player in players:
        points += player.current_rating

    return round(points / players_count, 2)


@register.filter(name="social_field")
def social_field (item, field):
    value = getattr(item, field)

    if not value:
        return ''
    
    icon_class_name = field.title().lower()
    if icon_class_name == 'website':
        icon_class_name = 'globe'
    elif icon_class_name == 'twitter':
        icon_class_name = 'twitter-x'

    return '<a target="_blank" href="' + value + '"  data-bs-toggle="tooltip"  data-bs-placement="top" title="' + field.title() + '"><i class="bi bi-'+ icon_class_name +'"></i></a>'


@register.filter(name="player_age_category")
def player_age_category (player):
    categories = {
        'JUN': [0,18],
        'ESP': [19,23],
        'SEN': [24,55],
        'VET': [56, 1000]
    }

    today = date.today()
    born = player.birth_date
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    for category, ages in categories.items():
        if ages[0] <= age <= ages[1]:
            return '<span class="badge bg-secondary">' + category + '</span>'

    return ''


@register.filter(name="season_player_age_category")
def season_player_age_category (player, year):
    categories = {
        'JUN': [0,18],
        'ESP': [19,23],
        'SEN': [24,55],
        'VET': [56, 1000]
    }

    today = date(int(year), 12, 31)
    born = player.birth_date
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    for category, ages in categories.items():
        if ages[0] <= age <= ages[1]:
            return '<span class="badge bg-secondary">' + category + '</span>'

    return ''


@register.filter(name="gender")
def gender (item):
    gender = item.gender

    gender_class = 'female'
    gender_label = _('Woman')
    if gender == 'M':
        gender_class = 'male'
        gender_label = _('Man')
    return '<span class="badge bg-secondary" data-bs-toggle="tooltip" data-bs-placement="top" title="'+ gender_label +'"><i class="bi bi-gender-'+ gender_class +'"></i> '+gender+'</span>'


@register.filter(name="licence_number")
def licence_number(item):
    if not item.is_licence_active:
        return '<span class="badge bg-danger" data-bs-toggle="tooltip" title="' + _('License') + '">' + _('No license') + '</span>'
    return '<span class="badge bg-primary" data-bs-toggle="tooltip" title="' + _('License') + '">' + str(item.licence_number) + '</span>'


@register.filter(name="is_active_player_class")
def is_active_player_class(item):
    if item.is_inclusive:
        return ''

    if not item.is_licence_active:
        return 'inactive'
    return ''


@register.filter(name="arbiter_label")
def arbiter_label(player):
    if not player.arbiter_level:
        return ''

    return f'''
        <dl class="row">
            <dt class="col-4">
                <a target="_blank" href="{reverse('arbiters')}">
                    {_("Arbiter category")}
                </a>
            </dt>
            <dd class="col-8">
                <span class="badge bg-primary">{player.get_arbiter_level_display()}</span>
            </dd>
        </dl>
    '''
    
@register.filter(name="player_sport_title_label")
def player_sport_title_label(player):
    if not player.sport_title:
        return ''

    return f'''
        <dl class="row">
            <dt class="col-4">
                <a target="_blank" href="{reverse('sport_titles')}">
                    {_("Sports title")}
                </a>
            </dt>
            <dd class="col-8">
                <span class="badge bg-primary">{player.get_sport_title_display()}</span>
            </dd>
        </dl>
    '''


@register.filter(name="coach_label")
def coach_label(player):
    if not player.coach_level:
        return ''

    return f'''
        <dl class="row">
            <dt class="col-4">
                <a target="_blank" href="{reverse('coaches')}">
                    {_("Coach category")}
                </a>
            </dt>
            <dd class="col-8">
                <span class="badge bg-secondary">{player.get_coach_level_display()}</span>
            </dd>
        </dl>
    '''


@register.filter(name="player_national_teams")
def player_national_teams(player):
    memberships = PlayerNational_teamMembership.objects.filter(player=player)

    if not memberships.exists():
        return ''

    html = f'''
        <dl class="row">
            <dt class="col-4">
                <a target="_blank" href="{reverse('national_teams')}">
                    {_("National teams")}
                </a>
            </dt>
            <dd class="col-8">
    '''

    for membership in memberships:
        html += f'''<span class="badge bg-success">{membership.team.name}: {membership.get_position_display()}</span>'''

    html += '</dd></dl>'

    return html



@register.filter(name="player_records")
def player_records(player):
    records = Record.objects.filter(player=player)

    if not records.exists():
        return ''

    html = f'''
        <dl class="row">
            <dt class="col-4">
                <a target="_blank" href="{reverse('records')}">
                    {_("National records")}
                </a>
            </dt>
            <dd class="col-8">
    '''

    for record in records:
        html += f'''<span class="badge bg-warning">{record.name}: {record.description}</span>'''

    html += '</dd></dl>'

    return html


@register.filter(name="tournament_field")
def tournament_field (item, field):
    value = getattr(item, field)
    model_field = Tournament._meta.get_field(field)
    label = str(model_field.verbose_name)
    value_type = model_field.get_internal_type()

    if field == "power":
        value = tournament_power_badge(item)
        label = _("Competition power")
    elif not value:
        return ''

    if field == "power":
        pass
    elif value_type == 'DateTimeField':
        value = formats.date_format(value, "SHORT_DATETIME_FORMAT")

    elif value_type == "DateField":
        value = formats.date_format(value, "SHORT_DATE_FORMAT")

    elif field == "place":
        value = str(value) + '''<a target="_blank" href="https://maps.google.com?q=''' + str(value) + '''">
                                    <span class="bi bi-globe"></span>
                                </a>'''

    elif field == "category":
        value = item.get_category_display()

    elif field == "format":
        value = item.get_format_display()
        
    elif field == "terms":
        if value:
            value = '''<a class="btn btn-sm btn-secondary" target="_blank" href="''' + value.url + '''"><i class="bi bi-download"></i> ''' + _('Download') + '''</a>'''


    if not value:
        return ''

    return '''
        <dt class="col-sm-5 fw-bold" title="''' + label + '''">''' + label + '''</dt>
        <dd class="col-sm-7">''' + str(value) + '''</dd>
    '''

@register.filter(name="team_short_name")
def team_short_name(team):
    return team.get_short_name()

@register.filter(name="team_short_name_in_tournament")
def team_short_name_in_tournament(tournament, player):
    all_player_teams = Team.objects.filter(players=player)
    team = TeamTournamentMembership.objects.get(tournament=tournament, team__in=all_player_teams)

    return team.team.get_short_name()

@register.filter(name="team_rating_points_in_tournament")
def team_rating_points_in_tournament(tournament, player):
    all_player_teams = Team.objects.filter(players=player)
    team = TeamTournamentMembership.objects.get(tournament=tournament, team__in=all_player_teams)

    return team.rating_points

@register.filter(name="team_power_in_tournament")
def team_power_in_tournament(tournament, player):
    all_player_teams = Team.objects.filter(players=player)
    team = TeamTournamentMembership.objects.get(tournament=tournament, team__in=all_player_teams)

    return team.power

@register.filter(name="team_min_place_in_tournament")
def team_min_place_in_tournament(tournament, player=False):

    if player:
        all_player_teams = Team.objects.filter(players=player)
        team = TeamTournamentMembership.objects.get(tournament=tournament, team__in=all_player_teams)
    else:
        team = tournament

    return str(team.place_min)

@register.filter(name="team_place_in_tournament")
def team_place_in_tournament(tournament, player=False):

    if player:
        all_player_teams = Team.objects.filter(players=player)
        team = TeamTournamentMembership.objects.get(tournament=tournament, team__in=all_player_teams)
    else:
        team = tournament

    message = '''
        <span class="badge bg-success" data-toggle="tooltip" data-placement="top" title="" data-original-title="''' + _('Place in competition') + '''">
    '''

    place = str(team.place_min)
    if team.place_max > 0:
        place = str(team.place_min)+"-"+str(team.place_max)

    message += place + '''
        </span>
    '''

    return message


@register.filter(name="team_place_in_tournament_for_admin")
def team_place_in_tournament_for_admin(tournament, player=False):
    if player:
        all_player_teams = Team.objects.filter(players=player)
        team = TeamTournamentMembership.objects.get(tournament=tournament, team__in=all_player_teams)
    else:
        team = tournament

    message = '''
        <div class="badge bg-success tournament-place-field">
            <input type="text" class="form-control form-control-sm tournament-place-field-min" 
                name="{team_pk}-min" value="{place_min}" 
                placeholder="{place_placeholder}"
                data-bs-toggle="tooltip" 
                data-bs-placement="top" 
                title="{place_title}" />
            - 
            <input type="text" class="form-control form-control-sm tournament-place-field-max" 
                name="{team_pk}-max" value="{place_max}" 
                placeholder="{place_max_placeholder}"
                data-bs-toggle="tooltip" 
                data-bs-placement="top" 
                title="{place_max_title}" />
        </div>
    '''.format(
        team_pk=team.pk, 
        place_min=team.place_min, 
        place_max=team.place_max,
        place_placeholder=_('Place'),
        place_title=_('Place in competition'),
        place_max_placeholder=_('Place (max)'),
        place_max_title=_('Place in competition (max). Leave 0 if not needed'),
    )

    return format_html(message)



@register.filter(name="tournaments_css_classes")
def tournaments_css_classes(tournament):
    classes = "tournament "

    if tournament.is_goes_to_rating:
        classes += "tournament_goes_to_rating "

    if tournament.is_ukrainian_league:
        classes += "tournament_ukrainian_league "

    if tournament.is_b_tournament:
        classes += "tournament_b "

    classes += " tournament_" + str(tournament.category)

    return classes


@register.filter(name="rating_points")
def rating_points(player, field_to_display):
    value = getattr(player, field_to_display)
    return str(value)

@register.filter(name="rating_power")
def rating_power(player, field_to_display):
    value = getattr(player, field_to_display)
    return str(value)


@register.filter(name="season_rating_points")
def season_rating_points(season_item, field_to_display):
    value = getattr(season_item, field_to_display)
    return str(value)


'''
Args[0] - rating field to display: current rating, b, liga etc.
Args[1] - "license" means that only licensed players participate in ranking. Other values look among all players
'''
@register.filter(name="rating_position")
def rating_position(player, args):
    args = [arg.strip() for arg in args.split(',')]

    field_to_display = 'current_rating'
    if len(args) >= 1 and args[0] != '':
        field_to_display = args[0]

    if len(args) >= 2 and (args[1] == 'licence' or args[1] == 'inclusive'):
        value = player.get_ranking(field_to_display)
    else:
        value = player.get_ranking_among_all(field_to_display)

    return str(value)


'''
Args[0] - rating field to display: current rating, b, liga etc.
Args[1] - year which should be used
'''
@register.filter(name="season_rating_position")
def season_rating_position(season_item, args):
    args = [arg.strip() for arg in args.split(',')]

    if len(args) <= 2 and args[1] == '':
        return 'error'

    field_to_display = 'rating'
    if len(args) >= 1 and args[0] != '':
        field_to_display = args[0]

    value = season_item.get_ranking(args[1], field_to_display)

    return str(value)


@register.filter(name="players_in_seasons")
def players_in_seasons(season, year):
    seasons_model = get_model('Season')
    players_count = seasons_model.objects.filter(year=year).count()
    return players_count


@register.filter(name="teams_count")
def teams_count(tournament):
    return tournament.get_teams_count()

@register.filter(name="tournament_display_name")
def tournament_display_name(tournament):
    return get_tournament_display_name(tournament)

@register.filter(name="tournament_card_metadata")
def tournament_card_metadata(tournament):
    return get_tournament_card_metadata(tournament)


@register.filter(name="tournament_audience_tag_class")
def tournament_audience_tag_class(tag):
    normalized_tag = str(tag or "").strip().lower()

    if normalized_tag in ("чоловіки", "men"):
        return "tournament-card-tag-men"
    if normalized_tag in ("жінки", "women"):
        return "tournament-card-tag-women"
    if normalized_tag in ("молодь", "юніори", "юнаки", "youth", "juniors", "cadets"):
        return "tournament-card-tag-youth"

    return ""


@register.filter(name="tournament_power_class")
def tournament_power_class(power):
    return _tournament_power_class(power)


@register.filter(name="tournament_power_badge")
def tournament_power_badge(tournament_or_power):
    power = getattr(tournament_or_power, "power", tournament_or_power)
    try:
        power_value = Decimal(str(power or 0))
    except (InvalidOperation, TypeError, ValueError):
        power_value = Decimal("0")

    if not power_value.is_finite() or power_value <= 0:
        return ""

    return format_html(
        '''
        <span class="badge tournament-power-badge {}" data-bs-toggle="tooltip" data-bs-placement="top" title="{}">
            <i class="bi bi-star"></i> <span class="tournament-power-label">{}</span> {}
        </span>
        ''',
        _tournament_power_class(power),
        _("Competition power"),
        _("Power"),
        _format_tournament_power(power),
    )


def _tournament_power_class(power):
    try:
        power_value = Decimal(str(power or 0))
    except (InvalidOperation, TypeError, ValueError):
        power_value = Decimal("0")

    if not power_value.is_finite() or power_value <= 0:
        return "tournament-power-none"
    if power_value <= Decimal("1.4883"):
        return "tournament-power-1"
    if power_value <= Decimal("3.9043"):
        return "tournament-power-2"
    if power_value <= Decimal("8.7510"):
        return "tournament-power-3"
    if power_value <= Decimal("12.8965"):
        return "tournament-power-4"
    if power_value <= Decimal("17.1797"):
        return "tournament-power-5"
    if power_value <= Decimal("20.4864"):
        return "tournament-power-6"
    if power_value <= Decimal("23.6641"):
        return "tournament-power-7"
    if power_value <= Decimal("29.0942"):
        return "tournament-power-8"
    if power_value < Decimal("40"):
        return "tournament-power-9"

    return "tournament-power-10"


def _format_tournament_power(power):
    try:
        power_value = Decimal(str(power or 0))
    except (InvalidOperation, TypeError, ValueError):
        power_value = Decimal("0")

    if not power_value.is_finite():
        power_value = Decimal("0")

    return formats.number_format(power_value, decimal_pos=2, force_grouping=False)


@register.filter(name="tournament_status")
def tournament_status(tournament):
    if tournament.is_processing_closed() and tournament.country == settings.CURRENT_COUNTRY:
        return ''
        
    button_class = "badge"
    message = ""
    icon_class = ""

    if tournament.is_processing_closed():
        # button_class += " bg-success"
        # icon_class = "bi bi-check2-circle"
        # message = "Змагання опрацьовано"
        pass
    elif tournament.is_finished():
        button_class += " bg-secondary"
        icon_class = "bi bi-clock"
        message = _("Competition is finished but not processed yet")
    elif tournament.is_began():
        button_class += " bg-danger"
        icon_class = "bi bi-lightning-fill"
        message = _("Competition is in progress")

    if message:
        return f'''
            <span class="{button_class}" data-bs-toggle="tooltip" data-bs-placement="top" title="{message}">
               <i class="{icon_class}"></i>
            </span>
        '''
    return ''



@register.filter(name="tournament_protocol")
def tournament_protocol(tournament):
    if not tournament.is_processing_closed():
        return ''

    return f'''
        <a target="_blank" href="{reverse('tournament_protocol', args=[tournament.pk])}">
            <span class="badge bg-success" data-bs-toggle="tooltip" data-bs-placement="top" title="{_("Competition protocol")}">
               <i class="bi bi-download"></i>
            </span>
        </a>
    '''



@register.filter(name="tournament_registration")
def tournament_registration(tournament):
    button_class = ""
    message = ""
    icon_class = ""

    if tournament.is_registration_opened():
        button_class = "badge bg-success tournament-register-button"
        icon_class = "bi bi-plus-lg"
        message = _("Registration is open until %(date)s") % {
            'date': format_datetime(tournament.date_registration_stop)
        }

    if message:
        return format_html(
            '''
                <a href="{}" class="{}" data-bs-toggle="tooltip" data-bs-placement="top" title="{}">
                   <i class="{}"></i> {}
                </a>
            ''',
            reverse('register_team', args=[tournament.pk]),
            button_class,
            message,
            icon_class,
            _("Register")
        )
    return ""


@register.filter(name="tournament_registration_badge")
def tournament_registration_badge(tournament):
    button_class = ""
    message = ""
    icon_class = ""

    if tournament.is_registration_opened():
        button_class = "badge bg-success"
        icon_class = "bi bi-plus-lg"
        message = _("Registration is open until %(date)s") % {
            'date': format_datetime(tournament.date_registration_stop)
        }

    if message:
        return format_html(
            '''
            <a href="{}">
                <span class="{}" data-bs-toggle="tooltip" data-bs-placement="top" title="{}">
                   <i class="{}"></i>
                </span>
            </a>
            ''',
            reverse('register_team', args=[tournament.pk]),
            button_class,
            message,
            icon_class
        )
    return ""


@register.filter(name="tournament_registration_button")
def tournament_registration_button(tournament):
    button_class = ""
    message = ""
    icon_class = ""

    if tournament.is_registration_opened():
        button_class = "btn btn-sm btn-success"
        icon_class = "bi bi-plus-lg"
        message = _("Registration is open until %(date)s") % {
            'date': format_datetime(tournament.date_registration_stop)
        }

    if message:
        return format_html(
            '''
            <a class="{}" data-bs-toggle="tooltip" data-bs-placement="top" title="{}" href="{}">
                <i class="{}"></i> {}
            </a>
            ''',
            button_class,
            message,
            reverse('register_team', args=[tournament.pk]),
            icon_class,
            _("Register")
        )
    return ""


@register.filter(name="tournament_registration_tab")
def tournament_registration_tab(tournament):
    if tournament.is_registration_opened():
        return '''
            <li class="nav-item no-tab-link">
                <a class="nav-link force-follow-link no-tab-link" href="''' + reverse('register_team', args=[tournament.pk]) + '''">
                    <i class="bi bi-plus-lg"></i> ''' + _("Register team") + '''
                </a>
            </li>
        '''
    return ''



@register.filter(name="get_role_in_department")
def get_role_in_department (player, department):
    department_role = PlayerDepartmentMembership.objects.filter(team=department, player=player)
    if not department_role[0]:
        return ''
    else:
        return department_role[0].role
    
@register.filter(name="get_description_in_department")
def get_description_in_department (player, department):
    department_description = PlayerDepartmentMembership.objects.filter(team=department, player=player)
    if not department_description[0]:
        return ''
    else:
        return department_description[0].description


@register.filter(name="get_order_in_department")
def get_order_in_department (player, department):
    department = PlayerDepartmentMembership.objects.filter(team=department, player=player)
    if not department[0]:
        return ''
    else:
        return department[0].order


@register.filter(name="is_tournament_in_player_rating")
def is_tournament_in_player_rating(tournament, player):
    if not player.current_rating_tournaments:
        return ""

    tournaments = json.loads(player.current_rating_tournaments)
    for t in tournaments:
        if t['tournament'] == tournament.pk:
            return "tournament_goes_to_rating"

    return ""


@register.filter(name="is_user_has_admin_access_to_tournament")
def is_user_has_admin_access_to_tournament(tournament, current_user):
    return tournament.is_user_has_admin_access_to_tournament(current_user)


@register.filter(name="is_user_has_admin_access_to_team")
def is_user_has_admin_access_to_team(team, current_user):
    return team.is_user_has_admin_access_to_team(current_user)

@register.filter(name="trim")
def trim(value):
    if isinstance(value, str):
        return value.strip()
    return value
