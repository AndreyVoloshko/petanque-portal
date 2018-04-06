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
    if request.POST.get('post'):
        for tournament in queryset:
            try:
                tournament.close_for_processing()
                messages.success(request, "Турнір '" + str(tournament.name) + "' зараховано і зактито")
            except Exception as e:
                messages.error(request, "Помилка під час зактиття турніру '" + str(tournament.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть зарахування і закриття турніру",
            'message': "Натупні <b>турніри буде закрито</b>:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'finish_processing'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

finish_processing.short_description = "Зарахувати бали та закрити турнір"


def erase_rating_points_and_powers(modeladmin, request, queryset):
    if request.POST.get('post'):
        for tournament in queryset:
            try:
                tournament.erase_rating_points_and_powers()
                messages.success(request, "Турнір '" + str(tournament.name) + "' обнулено")
            except Exception as e:
                messages.error(request, "Помилка під час обнулення рейтингу та сил турніру '" + str(tournament.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть обнулення рейтингових балів та сил",
            'message': "Натупні <b>турніри буде обнулено та перевідкрито</b>:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'erase_rating_points_and_powers'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

erase_rating_points_and_powers.short_description = "Обнулити рейтингові бали та сили"


def mark_as_ready_for_processing(modeladmin, request, queryset):
    if request.POST.get('post'):
        for tournament in queryset:
            try:

                tournament.mark_as_ready_for_processing()

                messages.success(request, "Турнір '" + str(tournament.name) + "' помічено як готовий до опрацювання")
            except Exception as e:
                messages.error(request, "Помилка під чаc помітки турніру '" + str(tournament.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть, що ви хочете змінити турніри'",
            'message': "Наступні турніри будуть помічені як 'готовий до опрацювання'",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'mark_as_ready_for_processing'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

mark_as_ready_for_processing.short_description = "Помітити як 'готовий до опрацювання'"


def full_power_and_rating_processing(modeladmin, request, queryset):
    if request.POST.get('post'):
        for tournament in queryset:
            try:

                tournament.recalculate_power()
                tournament.recalculate_ratings()
                tournament.close_for_processing()


                messages.success(request, "Рейтингові результати '" + str(tournament.name) + "' повністю перераховано")
            except Exception as e:
                messages.error(request, "Помилка під чаc повного циклу обробки турніру '" + str(tournament.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть запуск повного циклу обробки турніру",
            'message': "Для наступних турнірів будуть застововані наступні дії <ul><li>Перерахувати сили команд і турніру</li><li>Перерахувати рейтингові бали</li><li>Зарахувати бали та закрити турнір</li></ul>:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'full_power_and_rating_processing'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

full_power_and_rating_processing.short_description = "Зробити повний цикл перерахування сил та балів"


def erase_registration_dates(modeladmin, request, queryset):
    if request.POST.get('post'):
        for tournament in queryset:
            try:
                tournament.erase_registration_date()
                messages.success(request, "Дату реєстрації для Турніру '" + str(tournament.name) + "' обнулено")
            except Exception as e:
                messages.error(request, "Помилка під час обнулення дати реєстрації турніру '" + str(tournament.name) + "': " + str(e))
    else:
        context = {
            'title': "Підтвердіть обнулення дати реєстрації",
            'message': "Для наступних <b>турнірів дату реєстрації буде обнулено</b>:",
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'action': 'erase_registration_dates'
        }
        return TemplateResponse(request, 'admin/action_confirmation.html', context)

erase_registration_dates.short_description = "Обнулити дату реєстрації"
