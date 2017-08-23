from django import template
from django.conf import settings
import os.path
from federation.models.player import Player

register = template.Library()


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
        <i class="icon-flag icon-flag-'''+country.code+'''"></i>
    '''


@register.filter(name='club_logo')
def club_logo(club, additional_class=''):
    url = settings.MEDIA_ROOT + str(club.logo)

    if not os.path.isfile(url):
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

    if not os.path.isfile(url):
        url = settings.STATIC_URL + 'default.png'

    return '''
        <a href="/player/''' + str(user.id) + '''">
            <div class="logo-container user ''' + additional_class + '''">
                <img src=''' + url + ''' class="img-rounded" />
            </div>
        </a>
    '''


@register.filter(name='user_profile_link')
def user_profile_link(user):
    url = settings.MEDIA_ROOT + str(user.avatar)

    if not os.path.isfile(url):
        url = settings.STATIC_URL + 'default.png'

    return '<a href="/player/' + str(user.id) + '">' + user.get_name() + '</a>'

@register.filter(name="get_number_of_players")
def get_number_of_players (club):
    number_of_players = Player.objects.filter(current_club=club).count()
    return number_of_players

