from django.conf.urls import url
from .views.login import application_login
from .views.logout import application_logout
from .views.main_page import main_page
from .views.profile import profile
from .views.clubs import clubs, club
from .views.players import players, player
from .views.arbiters import arbiters
from .views.records import records


urlpatterns = [
    url(r'^$',          main_page,                 name='main_page'),

    url(r'^login/$',    application_login,         name='login'),
    url(r'^logout/$',   application_logout,        name='logout'),

    url(r'^profile/$',  profile,                   name='profile'),

    url(r'^clubs/$',    clubs,                     name='clubs'),
    url(r'^club/(?P<id>[0-9]+)$', club,            name='club'),

    url(r'^players/$',  players,                   name='players'),
    url(r'^player/(?P<id>[0-9]+)$', player,        name='player'),

    url(r'^national_teams/$', clubs,               name='national_teams'),
    url(r'^arbiters/$',     arbiters,              name='arbiters'),
    url(r'^records/$',     records,                name='records'),
]