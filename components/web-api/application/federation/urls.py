from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$',          views.federation_main_page,     name='main_page'),
    url(r'^login/$',    views.federation_login,         name='login'),
    url(r'^logout/$',   views.federation_logout,        name='logout'),
    url(r'^profile/$',  views.federation_profile,       name='profile'),
]