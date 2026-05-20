from django.conf import settings

def settings_context(request):
    return {
        "settings": settings,
        "federation_telegram_link": settings.FEDERATION_TELEGRAM_LINK,
    }
