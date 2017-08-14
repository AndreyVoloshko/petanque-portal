from django.conf.urls import url
from .views.login import application_login
from .views.logout import application_logout
from .views.main_page import main_page
from .views.profile import profile

urlpatterns = [
    url(r'^$',          main_page,                 name='main_page'),
    url(r'^login/$',    application_login,         name='login'),
    url(r'^logout/$',   application_logout,        name='logout'),
    url(r'^profile/$',  profile,                   name='profile'),
]