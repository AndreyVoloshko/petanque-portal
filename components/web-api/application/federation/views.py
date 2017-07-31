from django.shortcuts import render
from django_bootstrap_carousel.models import Carousel

from django.http import *
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from federation.models import Player, Club
from django_countries.data import COUNTRIES

# Create your views here.
def federation_main_page(request):
    carousel = Carousel.objects.get(pk=1)
    return render(request, 'main_page.html', {
            'carousel': carousel,
        })

def federation_login(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/profile/')

    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect('/profile/')

    return render(request, 'login.html', {})

@login_required(login_url='/login/')
def federation_logout(request):
    logout(request)
    return HttpResponseRedirect('/')

@login_required(login_url='/login/')
def federation_profile(request):
    player = get_object_or_404(Player, user=request.user)

    clubs = Club.objects.all()
    countries = COUNTRIES
    return render(request, 'profile.html', {
            'user': player,
            'clubs': clubs,
            'countries': countries
        })