from django.contrib import messages
from federation.helpers.general import get_model

def save_current_ratings(modeladmin, request, queryset):
    try:
        seasons_model = get_model('Season')

        seasons_model.save_current_ratings(seasons_model)

        messages.success(request, "Рейтигові позиції збережено")
    except Exception as e:
        messages.error(request, "Помилка під час зберігання рейтигових позицій: " + str(e))

save_current_ratings.short_description = "Записати цьогорічні рейтинги"


