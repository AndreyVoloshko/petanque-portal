"""api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.urls import include, path, re_path
from django.contrib import admin
from django.conf import settings
from django.contrib.staticfiles.views import serve as serve_static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    re_path(r'', include('federation.urls'))
]

if settings.STATIC_URL == '/static/':
    urlpatterns.insert(
        0,
        re_path(r'^static/(?P<path>.*)$', serve_static, {'insecure': True}),
    )

urlpatterns += staticfiles_urlpatterns()
