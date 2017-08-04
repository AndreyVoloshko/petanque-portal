from django.shortcuts import render
from django_bootstrap_carousel.models import Carousel

from django.http import *
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from .models import Player
from .forms import PlayerForm, AuthorizationProfileForm
from django.contrib.auth import update_session_auth_hash


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

    if request.method == "POST":
        if 'name' in request.POST:
            profile_form = PlayerForm(request.POST, request.FILES, instance=player)
            if profile_form.is_valid():
                player = profile_form.save(commit=False)
                player.avatar = profile_form.cleaned_data['avatar']
                player.save()

        if 'old_password' in request.POST:
            authorization_profile_form = AuthorizationProfileForm(request.user, request.POST)
            if authorization_profile_form.is_valid():
                user = authorization_profile_form.save()
                update_session_auth_hash(request, user)


    profile_form = PlayerForm(instance=player)
    authorization_profile_form = AuthorizationProfileForm(request.user)

    return render(request, 'profile.html', {
            'user': player,
            'profile_form': profile_form,
            'authorization_profile_form': authorization_profile_form
        })