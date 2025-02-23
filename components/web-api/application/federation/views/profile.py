from django.shortcuts import render

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from federation.models.player import Player
from federation.forms.player_form import PlayerForm
from federation.forms.authorization_profile_form import AuthorizationProfileForm
from django.contrib.auth import update_session_auth_hash

@login_required(login_url='/login/')
def profile(request):
    player = get_object_or_404(Player, user=request.user)

    profile_form = PlayerForm(instance=player)
    authorization_profile_form = AuthorizationProfileForm(request.user)

    if request.method == "POST":
        if 'name' in request.POST:
            profile_form = PlayerForm(request.POST, request.FILES, instance=player)
            if profile_form.is_valid():
                if profile_form.cleaned_data.get('avatar') is False:
                    player.avatar = None
                else:
                    player.avatar = profile_form.cleaned_data['avatar']
                player = profile_form.save(commit=False)
                player.save()
                profile_form = PlayerForm(request.POST, request.FILES, instance=player)
                messages.success(request, 'Профiль змiнено.')

        if 'old_password' in request.POST:
            authorization_profile_form = AuthorizationProfileForm(request.user, request.POST)
            if authorization_profile_form.is_valid():
                user = authorization_profile_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Пароль змiнено.')

    return render(request, 'profile.html', {
            'player': player,
            'profile_form': profile_form,
            'authorization_profile_form': authorization_profile_form
        })