import hashlib
from functools import lru_cache

from django.conf import settings
from django.contrib.staticfiles import finders


@lru_cache(maxsize=None)
def _static_asset_version(static_path):
    asset_path = finders.find(static_path)
    if not asset_path:
        return getattr(settings, 'STATIC_ASSET_VERSION', 'local')

    with open(asset_path, 'rb') as asset:
        return hashlib.sha256(asset.read()).hexdigest()[:12]


def settings_context(request):
    return {
        "settings": settings,
        "federation_telegram_link": settings.FEDERATION_TELEGRAM_LINK,
        "static_asset_versions": {
            "portal_ui": _static_asset_version('portal-ui.js'),
            "style_v2": _static_asset_version('style-v2.css'),
        },
    }
