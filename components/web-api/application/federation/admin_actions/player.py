from django.contrib import messages
from django.template.response import TemplateResponse
from django.contrib.admin import helpers

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