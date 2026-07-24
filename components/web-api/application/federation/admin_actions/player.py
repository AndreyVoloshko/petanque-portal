from django import forms
from django.contrib import messages
from django.template.response import TemplateResponse
from django.contrib.admin import helpers
from federation.audit import record_player_change
from federation.models.club import Club


def recalculate_ratings(modeladmin, request, queryset):
    if request.POST.get('post'):
        for player in queryset:
            try:
                player.recalculate_ratings()
                messages.success(request, "Рейтинг гравця '" + str(player.name) + "' перераховано")
            except Exception as e:
                messages.error(request, "Помилка під час перерахування рейтингу гравця '" + str(player.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть перерахування рейтингу гравців",
            'message': "<b>Рейтингові бали будуть перераховані</b> для наступних гравців:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'recalculate_ratings'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

recalculate_ratings.short_description = "Перерахувати рейтингові бали"


def erase_ratings(modeladmin, request, queryset):
    if request.POST.get('post'):
        for player in queryset:
            try:
                player.erase_ratings()
                messages.success(request, "Рейтинг гравця '" + str(player.name) + "' обнулено")
            except Exception as e:
                messages.error(request, "Помилка під час обнулення рейтингу гравця '" + str(player.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть обнулення рейтингових балів гравцям",
            'message': "<b>Рейтингові бали будуть обнулено</b> для наступних гравців:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'erase_ratings'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

erase_ratings.short_description = "Обнулити рейтингові бали"


def _run_audited_player_action(request, player, action):
    """Run a saving player action while retaining values needed for revert."""
    player_before = player.__class__.objects.select_related('user').get(pk=player.pk)
    action()
    record_player_change(request.user, player_before, player)


def activate_licence(modeladmin, request, queryset):
    if request.POST.get('post'):
        for player in queryset:
            try:
                _run_audited_player_action(
                    request,
                    player,
                    player.activate_licence,
                )
                messages.success(request, "Ліцензію гравця '" + str(player.name) + "' активовано")
            except Exception as e:
                messages.error(request, "Помилка під час активації ліцензії гравця '" + str(player.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть активування ліцензій гравцям",
            'message': "<b>Ліцензію буде активовано</b> для наступних гравців:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'activate_licence'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

activate_licence.short_description = "Активувати ліцензію"


def deactivate_licence(modeladmin, request, queryset):
    if request.POST.get('post'):
        for player in queryset:
            try:
                _run_audited_player_action(
                    request,
                    player,
                    player.deactivate_licence,
                )
                messages.success(request, "Ліцензію гравця '" + str(player.name) + "' деактивовано")
            except Exception as e:
                messages.error(request, "Помилка під час деактивації ліцензії гравця '" + str(player.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть деактивацію ліцензій гравцям",
            'message': "<b>Ліцензію буде деактивовано</b> для наступних гравців:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'deactivate_licence'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

deactivate_licence.short_description = "Деактивувати ліцензію"


def erase_licence_number(modeladmin, request, queryset):
    if request.POST.get('post'):
        for player in queryset:
            try:
                _run_audited_player_action(
                    request,
                    player,
                    player.erase_licence_number,
                )
                messages.success(request, "Ліцензію гравця '" + str(player.name) + "' обнулено")
            except Exception as e:
                messages.error(request, "Помилка під час обнулення ліцензії гравця '" + str(player.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть обнулення ліцензії гравцям",
            'message': "<b>Ліцензії будуть обнулено</b> для наступних гравців:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'erase_licence_number'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)


class SetClubActionForm(forms.Form):
    club = forms.ModelChoiceField(
        queryset=Club.objects.filter(is_active=True).order_by('name'),
        label='Клуб',
    )


def set_club(modeladmin, request, queryset):
    """Reassign selected players to one club without opening each of them."""
    if request.POST.get('post'):
        form = SetClubActionForm(request.POST)
        if form.is_valid():
            club = form.cleaned_data['club']
            for player in queryset:
                try:
                    def apply_club(player=player, club=club):
                        player.current_club = club
                        player.save()

                    _run_audited_player_action(request, player, apply_club)
                    messages.success(request, "Клуб гравця '" + str(player.name) + "' змінено на '" + str(club.name) + "'")
                except Exception as e:
                    messages.error(request, "Помилка під час зміни клубу гравця '" + str(player.name) + "': " + str(e))
            return None
    else:
        form = SetClubActionForm()

    context = {
        'title': "Оберіть клуб для обраних гравців",
        'message': "<b>Клуб буде змінено</b> для наступних гравців:",
        'form': form,
        'queryset': queryset,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        'action': 'set_club',
    }
    return TemplateResponse(request, 'admin/set_club_action.html', context)

set_club.short_description = "Змінити клуб для обраних гравців"

erase_licence_number.short_description = "Обнулити ліцензію"
