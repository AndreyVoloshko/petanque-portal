from django.contrib import messages
from django.template.response import TemplateResponse
from django.contrib.admin import helpers
from federation.audit import (
    PLAYER_CHANGE_LICENCE_NUMBER_FIELDS,
    PLAYER_CHANGE_LICENCE_STATUS_FIELDS,
    capture_player_change_values,
    log_player_change,
)


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


def _run_audited_player_action(request, player, changed_fields, action):
    """Run a saving player action while retaining values needed for revert."""
    player_before = player.__class__.objects.select_related('user').get(pk=player.pk)
    action()
    field_values = capture_player_change_values(player_before, player, changed_fields)
    log_player_change(request.user, player, field_values, field_values=field_values)


def activate_licence(modeladmin, request, queryset):
    if request.POST.get('post'):
        for player in queryset:
            try:
                _run_audited_player_action(
                    request,
                    player,
                    PLAYER_CHANGE_LICENCE_STATUS_FIELDS,
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
                    PLAYER_CHANGE_LICENCE_STATUS_FIELDS,
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
                    PLAYER_CHANGE_LICENCE_NUMBER_FIELDS,
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

erase_licence_number.short_description = "Обнулити ліцензію"
