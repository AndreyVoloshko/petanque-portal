from django.shortcuts import render
from django.template import RequestContext
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.auth import views as auth_views
from django.urls import re_path, include, path
from .views.login import application_login
from .views.logout import application_logout
from .views.main_page import main_page
from .views.profile import profile
from .views.clubs import clubs, club
from .views.players import players, player
from .views.arbiters import arbiters
from .views.coaches import coaches
from .views.records import records
from .views.sport_titles import sport_titles
from .views.tournaments import tournaments, tournament, tournaments_calendar, tournament_teams_export, tournament_protocol
from .views.api import tournaments_list, players_clubs_and_tournaments_list, players_list, submit_tournament_results
from .views.documents import documents
from .views.national_teams import national_teams
from .views.seasons import seasons
from .views.register import register_team, register_player
from .views.departments import departments
from .views.statistics import statistics
from .views.email_confirm import email_prompt, email_confirm
from .views.password_reset import CustomPasswordResetConfirmView, CustomPasswordResetView


urlpatterns = [
    re_path(r'^$',          main_page,                 name='main_page'),

    re_path(r'^login/$',    application_login,         name='login'),
    re_path(r'^logout/$',   application_logout,        name='logout'),

    path('password-reset/', CustomPasswordResetView.as_view(
        template_name='password_reset/request.html',
        email_template_name='password_reset/email_body.html',
        html_email_template_name='password_reset/email_body.html',
        subject_template_name='password_reset/email_subject.txt',
        success_url='/password-reset/done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset/done.html',
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(
        template_name='password_reset/confirm.html',
        success_url='/password-reset/complete/',
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset/complete.html',
    ), name='password_reset_complete'),

    path('email/prompt/', email_prompt, name='email_prompt'),
    path('email/confirm/<uuid:token>/', email_confirm, name='email_confirm'),

    re_path(r'^profile/$',  profile,                   name='profile'),

    re_path(r'^clubs/$',    clubs,                     name='clubs'),
    re_path(r'^club/(?P<id>[0-9]+)$', club,            name='club'),

    re_path(r'^players/$',  players,                   name='players'),
    re_path(r'^players/(?P<licence_filter>\w+)/?$', players, name='players'),
    re_path(r'^players/(?P<licence_filter>\w+)/(?P<rating_filter>\w+)/?$', players, name='players'),

    re_path(r'^player/(?P<id>[0-9]+)$', player,        name='player'),

    re_path(r'^tournament/(?P<id>[0-9]+)$', tournament,        name='tournament'),
    re_path(r'^tournament/team_export/(?P<id>[0-9]+)$', tournament_teams_export, name='tournament_teams_export'),
    re_path(r'^tournament/tournament_protocol/(?P<id>[0-9]+)$', tournament_protocol, name='tournament_protocol'),
    re_path(r'^tournaments/$',                            tournaments, name='tournaments'),
    re_path(r'^tournaments/(?P<date_filter>\w+)/?$',               tournaments, name='tournaments'),
    re_path(r'^tournaments/(?P<date_filter>\w+)/(?P<type_filter>\w+)/?$', tournaments, name='tournaments'),

    re_path(r'^register/team/(?P<tournament_id>\w+)/?$', register_team, name='register_team'),
    re_path(r'^register/player/?$', register_player, name='register_player'),

    re_path(r'^calendar/$', tournaments_calendar, name='tournaments_calendar'),
    re_path(r'^api/tournaments/list/$', tournaments_list, name='api_tournaments_list'),
    re_path(r'^api/players_clubs_and_tournaments/list/$', players_clubs_and_tournaments_list, name='api_players_clubs_and_tournaments_list'),
    re_path(r'^api/players_list/list/$', players_list, name='api_players_list'),
    re_path(r'^api/tournament/results/$', submit_tournament_results, name='api_submit_tournament_results'),

    re_path(r'^national_teams/$', national_teams, name='national_teams'),
    re_path(r'^national_teams/(?P<team_id>\w+)/?$', national_teams, name='national_teams'),

    re_path(r'^arbiters/$',     arbiters,              name='arbiters'),
    re_path(r'^coaches/$',      coaches,               name='coaches'),
    re_path(r'^records/$',     records,                name='records'),
    re_path(r'^sport_titles/$', sport_titles,          name='sport_titles'),

    re_path(r'^documents/$',     documents,                name='documents'),

    re_path(r'^departments/$', departments, name='departments'),

    re_path(r'^season/?$', seasons, name='season'),
    re_path(r'^season/(?P<year>\w+)/?$', seasons, name='season'),

    re_path(r'^statistics/$', statistics, name='statistics'),
    re_path(r'^statistics/(?P<year>\w+)/?$', statistics, name='statistics'),
    
    path('captcha/', include('captcha.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


def handler404(request):
    response = render(request, '404.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response


def handler500(request):
    response = render(request, '500.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 500
    return response
