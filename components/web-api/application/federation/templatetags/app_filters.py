from django import template
from django.conf import settings
import os.path
from federation.models.team import Team
from federation.models.player import Player
from federation.models.record import Record
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from federation.models.national_teams import National_team, PlayerNational_teamMembership
from datetime import date
from django.utils import formats
from federation.helpers.general import get_model

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


@register.filter(name='get_year')
def get_year(value):
    return value.strftime('%Y')


@register.filter(name='country_icon')
def country_icon(country):
    return '''
        ''' + str(country.name) + '''&nbsp;<i class="icon-flag icon-flag-'''+country.code+'''"></i>
    '''

@register.filter(name='country_flag')
def country_flag(country):
    return '''
        &nbsp;<i data-toggle="tooltip" data-placement="top" title="" data-original-title="''' + str(country.name) + '''" class="icon-flag icon-flag-'''+country.code+'''"></i>
    '''


@register.filter(name='club_logo')
def club_logo(club, additional_class=''):
    url = settings.MEDIA_ROOT + str(club.logo)

    if not club.logo:
        url = settings.STATIC_URL + 'default.png'

    return '''
        <a href="/club/''' + str(club.id) + '''">
            <div class="logo-container club ''' + additional_class + '''">
                <img src=''' + url + ''' class="img-rounded" />
            </div>
        </a>
    '''


@register.filter(name='user_avatar')
def user_avatar(user, additional_class=''):
    url = settings.MEDIA_ROOT + str(user.avatar)

    if not user.avatar:
        url = settings.STATIC_URL + 'default.png'

    return '''
        <a href="/player/''' + str(user.id) + '''">
            <div class="logo-container user ''' + additional_class + '''">
                <img src=''' + url + ''' class="img-rounded" />
            </div>
        </a>
    '''


@register.filter(name='user_profile_link')
def user_profile_link(user, is_link=True):
    if not is_link:
        return user.get_name()
    return '<a href="/player/' + str(user.id) + '">' + user.get_name() + '</a>'


@register.filter(name="get_number_of_players")
def get_number_of_players (club):
    number_of_players = Player.objects.filter(current_club=club).count()
    return number_of_players


@register.filter(name="social_field")
def social_field (item, field):
    value = getattr(item, field)

    if not value :
        return ''

    return '''
        <div class="row social-field">
            <div class="col-sm-4">''' + field.title() + '''</div>
            <div class="col-sm-8">
                <a target="_blank" title="''' + value + '''" href="''' + value + '''">''' + value + '''</a>
            </div>
        </div>    
    '''


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
            return '<span class="btn btn-warning btn-xs">' + category + '</span>'

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
            return '<span class="btn btn-warning btn-xs">' + category + '</span>'

    return ''


@register.filter(name="gender")
def gender (item):
    gender = item.gender

    gender_class = 'primary'
    if gender == 'M':
        gender_class = 'success'
    return '<span class="btn btn-' + gender_class + ' btn-xs">' + gender + '</span>'


@register.filter(name="licence_number")
def licence_number(item):
    if not item.licence_number:
        return '<span class="btn btn-danger btn-xs">Без ліцензії</span>'
    return '<span class="btn btn-xs btn-info">' + item.licence_number + '</span>'


@register.filter(name="is_active_player_class")
def is_active_player_class(item):
    if not item.licence_number:
        return 'inactive'
    return ''


@register.filter(name="arbiter_label")
def arbiter_label (player):
    if not player.arbiter_level :
        return ''

    return '''
    <div class="col-sm-2">
        <div class="row social-field">
            <div class="col-sm-12">
                Арбітр <a target="_blank" href="{% url 'arbiters' %}"><i class="glyphicon glyphicon-link"></i></a>:<br />
                <div class="btn btn-xs btn-success label-list-record">''' + player.get_arbiter_level_display() + '''</div>
            </div>
        </div>    
    </div>
    '''

@register.filter(name="coach_label")
def coach_label (player):
    if not player.coach_level :
        return ''

    return '''
    <div class="col-sm-2">
        <div class="row social-field">
            <div class="col-sm-12">
                Тренер <a target="_blank" href="{% url 'coaches' %}"><i class="glyphicon glyphicon-link"></i></a>:<br />
                <div class="btn btn-xs btn-info label-list-record">''' + player.get_coach_level_display() + '''</div>
            </div>
        </div>  
    </div>  
    '''


@register.filter(name="player_national_teams")
def player_national_teams(player):
    memberships = PlayerNational_teamMembership.objects.filter(player__in=[player])

    if not memberships:
        return ''

    html = '''
    <div class="col-sm-4">
        <div class="row social-field">
            <div class="col-sm-12">
            Національні збірні <a target="_blank" href="/national_teams/"><i class="glyphicon glyphicon-link"></i></a>:<br />'''

    for membership in memberships:
        html += '''<div class="btn btn-xs btn-primary label-list-record">''' + membership.team.name + ''': ''' + membership.get_position_display()

        html += '''</div><br />'''

    html += '</div></div></div>'

    return html


@register.filter(name="player_records")
def player_records(player):
    records = Record.objects.filter(player=player)

    if not records:
        return ''

    html = '''
    <div class="col-sm-4">
        <div class="row social-field">
            <div class="col-sm-12">
            Рекорди України <a target="_blank" href="/records/"><i class="glyphicon glyphicon-link"></i></a>:<br />'''

    for record in records:
        html += '''<div class="btn btn-xs btn-warning label-list-record">''' + record.name + ''': ''' + record.description + '''</div><br />'''

    html += '</div></div></div>'

    return html

@register.filter(name="tournament_field")
def tournament_field (item, field):
    value = getattr(item, field)
    value_type = Tournament._meta.get_field(field).get_internal_type()

    if value_type == 'DateTimeField':
        value = formats.date_format(value, "SHORT_DATETIME_FORMAT")

    elif value_type == "DateField":
        value = formats.date_format(value, "SHORT_DATE_FORMAT")

    elif field == "place":
        value = str(value) + '''<a target="_blank" href="https://maps.google.com?q=''' + str(value) + '''">
                                    <span class="glyphicon glyphicon glyphicon-globe"></span>
                                </a>'''

    elif field == "category":
        value = item.get_category_display()

    elif field == "format":
        value = item.get_format_display()


    if not value:
        return ''

    return '''
        <dt title="''' + str(Tournament._meta.get_field(field).verbose_name) + '''">''' + str(Tournament._meta.get_field(field).verbose_name) + '''</dt>
        <dd>''' + str(value) + '''</dd>
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
        <span class="btn btn-primary btn-xs" data-toggle="tooltip" data-placement="top" title="" data-original-title="Місце у турнірі">
    '''

    place = str(team.place_min)
    if team.place_max > 0:
        place = str(team.place_min)+"-"+str(team.place_max)

    message += place + '''
        </span>
    '''

    return message


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

    if len(args) >= 2 and args[1] == 'licence':
        value = player.get_ranking(field_to_display)
    else:
        value = player.get_ranking_among_all(field_to_display)

    return "<b>" + str(value) + "</b>"


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

@register.filter(name="tournament_status")
def tournament_status(tournament):
    button_class=""
    message=""
    icon_class=""

    if tournament.is_processing_closed():
        button_class = "btn btn-success btn-xs"
        icon_class = "glyphicon glyphicon glyphicon-check"
        message = "Турнір опрацьовано"
    elif tournament.is_finished():
        button_class = "btn btn-default btn-xs"
        icon_class = "glyphicon glyphicon glyphicon-time"
        message = "Турнір завершено, але ще не опрацьовано"
    elif tournament.is_began():
        button_class = "btn btn-danger btn-xs"
        icon_class = "glyphicon glyphicon glyphicon-flash"
        message = "Турнір проходить зараз"

    if message != "":
        return '''
            <div class="''' + button_class + '''" data-toggle="tooltip" data-placement="top" title="" data-original-title="''' + message + '''">
               <span class="''' + icon_class + '''"></span> i
            </div>
        '''
    else:
        return ''
