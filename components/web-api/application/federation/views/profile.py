from django.shortcuts import render

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from federation.models.player import Player
from federation.forms.player_form import PlayerForm
from federation.forms.authorization_profile_form import AuthorizationProfileForm
from django.contrib.auth import update_session_auth_hash
from django.utils.translation import gettext_lazy as _
from federation.audit import (
    PLAYER_CHANGE_FIELD_PASSWORD,
    capture_player_change_values,
    log_player_change,
)

@login_required(login_url='/login/')
def profile(request):
    player = get_object_or_404(Player, user=request.user)

    profile_form = PlayerForm(instance=player)
    authorization_profile_form = AuthorizationProfileForm(request.user)

    if request.method == "POST":
        if 'name' in request.POST:
            profile_form = PlayerForm(request.POST, request.FILES, instance=player)
            if profile_form.is_valid():
                with transaction.atomic():
                    player_before = Player.objects.select_related('user').select_for_update().get(pk=player.pk)
                    changed_fields = profile_form.changed_data
                    if profile_form.cleaned_data.get('avatar') is False:
                        player.avatar = None
                    else:
                        player.avatar = profile_form.cleaned_data['avatar']
                    player = profile_form.save(commit=False)
                    player.save()
                    field_values = capture_player_change_values(player_before, player, changed_fields)
                    log_player_change(request.user, player, field_values, field_values=field_values)
                profile_form = PlayerForm(request.POST, request.FILES, instance=player)
                messages.success(request, _('Profile updated.'))

        if 'old_password' in request.POST:
            authorization_profile_form = AuthorizationProfileForm(request.user, request.POST)
            if authorization_profile_form.is_valid():
                with transaction.atomic():
                    user = authorization_profile_form.save()
                    log_player_change(request.user, player, [PLAYER_CHANGE_FIELD_PASSWORD])
                update_session_auth_hash(request, user)
                messages.success(request, _('Password changed.'))

    return render(request, 'profile.html', {
            'player': player,
            'profile_form': profile_form,
            'authorization_profile_form': authorization_profile_form
        })
