from django.contrib import messages
from django.template.response import TemplateResponse
from django.contrib.admin import helpers


def recalculate_power(modeladmin, request, queryset):
    if request.POST.get('post'):
        for tournament in queryset:
            try:
                tournament.recalculate_power()
                messages.success(request, "Перераховано силу турніру '" + str(tournament.name) + "'")
            except Exception as e:
                messages.error(request, "Помилка перерахування сили турніру '" + str(tournament.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть перерахування сил команд",
            'message': "<b>Сили будуть перераховано</b> для наступних турнірів:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'recalculate_power'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

recalculate_power.short_description = "Перерахувати сили команд і турніру"


def recalculate_ratings(modeladmin, request, queryset):
    if request.POST.get('post'):
        for tournament in queryset:
            try:
                tournament.recalculate_ratings()
                messages.success(request, "Рейтингові бали за турнір '" + str(tournament.name) + "' перераховано")
            except Exception as e:
                messages.error(request, "Помилка перерахування рейтингових балів за турнір '" + str(tournament.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть перерахування рейтингових балів",
            'message': "<b>Рейтингові бали будуть нараховані</b> для наступних турнірів:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'recalculate_ratings'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

recalculate_ratings.short_description = "Перерахувати рейтингові бали"


def finish_processing(modeladmin, request, queryset):
    print("close")

finish_processing.short_description = "Зарахувати бали та закрити турнір"