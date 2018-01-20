from django.contrib import messages


def recalculate_power (modeladmin, request, queryset):
    log = "This is a log for: "
    for tournament in queryset:
        log += str(tournament.pk)

    messages.info(request, log)
    messages.info(request, log)
    messages.info(request, log)

recalculate_power.short_description = "Перерахувати сили команд і турніру"


def recalculate_ratings (modeladmin, request, queryset):
    print("rating")

recalculate_ratings.short_description = "Перерахувати рейтингові бали"


def finish_processing (modeladmin, request, queryset):
    print("close")

finish_processing.short_description = "Зарахувати бали та закрити турнір"