from django.conf.urls import url
from .views.login import application_login
from .views.logout import application_logout
from .views.main_page import main_page
from .views.profile import profile
from .views.clubs import clubs, club


urlpatterns = [
    url(r'^$',          main_page,                 name='main_page'),

    url(r'^login/$',    application_login,         name='login'),
    url(r'^logout/$',   application_logout,        name='logout'),

    url(r'^profile/$',  profile,                   name='profile'),

    url(r'^clubs/$',    clubs,                     name='clubs'),
    url(r'^club/(?P<id>[0-9]+)$', club,            name='club'),

    url(r'^players/$',  clubs,                     name='players'),
    url(r'^player/(?P<id>[0-9]+)$', club,          name='player'),
]