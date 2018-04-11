from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings
from django.conf.urls.static import static

from django.conf.urls import url, include
from .views.login import application_login
from .views.logout import application_logout
from .views.main_page import main_page
from .views.profile import profile
from .views.clubs import clubs, club
from .views.players import players, player
from .views.arbiters import arbiters
from .views.coaches import coaches
from .views.records import records
from .views.tournaments import tournaments, tournament, tournaments_calendar, tournament_teams_export
from .views.api import tournaments_list, players_clubs_and_tournaments_list, players_list
from .views.polls import poll, vote, result
from .views.documents import documents
from .views.national_teams import national_teams
from .views.seasons import seasons
from .views.register import register_team


urlpatterns = [
    url(r'^$',          main_page,                 name='main_page'),

    url(r'^login/$',    application_login,         name='login'),
    url(r'^logout/$',   application_logout,        name='logout'),

    url(r'^profile/$',  profile,                   name='profile'),

    url(r'^clubs/$',    clubs,                     name='clubs'),
    url(r'^club/(?P<id>[0-9]+)$', club,            name='club'),

    url(r'^players/$',  players,                   name='players'),
    url(r'^players/(?P<licence_filter>\w+)/?$', players, name='players'),
    url(r'^players/(?P<licence_filter>\w+)/(?P<rating_filter>\w+)/?$', players, name='players'),

    url(r'^player/(?P<id>[0-9]+)$', player,        name='player'),

    url(r'^tournament/(?P<id>[0-9]+)$', tournament,        name='tournament'),
    url(r'^tournament/team_export/(?P<id>[0-9]+)$', tournament_teams_export,        name='tournament_teams_export'),
    url(r'^tournaments/$',                            tournaments, name='tournaments'),
    url(r'^tournaments/(?P<date_filter>\w+)/?$',               tournaments, name='tournaments'),
    url(r'^tournaments/(?P<date_filter>\w+)/(?P<type_filter>\w+)/?$', tournaments, name='tournaments'),

    url(r'^register/team/(?P<tournament_id>\w+)/?$', register_team, name='register_team'),

    url(r'^calendar/$', tournaments_calendar, name='tournaments_calendar'),
    url(r'^api/tournaments/list/$', tournaments_list, name='api_tournaments_list'),
    url(r'^api/players_clubs_and_tournaments/list/$', players_clubs_and_tournaments_list, name='api_players_clubs_and_tournaments_list'),
    url(r'^api/players_list/list/$', players_list, name='api_players_list'),

    url(r'^national_teams/$', national_teams, name='national_teams'),
    url(r'^national_teams/(?P<team_id>\w+)/?$', national_teams, name='national_teams'),

    url(r'^arbiters/$',     arbiters,              name='arbiters'),
    url(r'^coaches/$',      coaches,               name='coaches'),
    url(r'^records/$',     records,                name='records'),

    url(r'^polls/vote/(?P<poll_pk>\d+)/$', vote, name='poll_ajax_vote'),
    url(r'^polls/poll/(?P<poll_pk>\d+)/$', poll, name='poll'),
    url(r'^polls/result/(?P<poll_pk>\d+)/$', result, name='poll_result'),

    url(r'^documents/$',     documents,                name='documents'),

    url(r'^season/?$', seasons, name='season'),
    url(r'^season/(?P<year>\w+)/?$', seasons, name='season'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

def handler404(request):
    response = render_to_response('404.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response


def handler500(request):
    response = render_to_response('500.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 500
    return response