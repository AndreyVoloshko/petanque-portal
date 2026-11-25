import hashlib
from functools import lru_cache

from django.conf import settings
from django.contrib.staticfiles import finders


DIRECTORY_ROUTES = {'departments', 'arbiters', 'coaches', 'national_teams', 'sport_titles'}


@lru_cache(maxsize=None)
def _static_asset_version(static_path):
    asset_path = finders.find(static_path)
    if not asset_path:
        return getattr(settings, 'STATIC_ASSET_VERSION', 'local')

    with open(asset_path, 'rb') as asset:
        return hashlib.sha256(asset.read()).hexdigest()[:12]


def settings_context(request):
    route = request.resolver_match.url_name if request.resolver_match else ''
    return {
        "portal_ui": {
            "club_directory": route == "clubs",
            "club_profile": route == "club",
            "player_profile": route == "player",
            "tournament_detail": route == "tournament",
            "team_registration": route == "register_team",
            "home_page": route == "main_page",
            "directory": route in DIRECTORY_ROUTES,
            "athlete_card": route in DIRECTORY_ROUTES or route in {'main_page', 'club', 'tournament'},
            "rating_styles": route in {'clubs', 'player', 'tournament'},
        },
        "settings": settings,
        "federation_telegram_link": settings.FEDERATION_TELEGRAM_LINK,
        "static_asset_versions": {
            "header": _static_asset_version("header.js"),
            "home_carousel": _static_asset_version("home-carousel.js"),
            "list_navigation": _static_asset_version("list-navigation.js"),
            "portal_ui": _static_asset_version('portal-ui.js'),
            "style_v2": _static_asset_version('style-v2.css'),
        },
    }
