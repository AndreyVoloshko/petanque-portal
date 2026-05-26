from django.conf import settings
from django.utils.cache import patch_vary_headers
from django.utils.translation import check_for_language


COUNTRY_HEADER_CANDIDATES = (
    'HTTP_CF_IPCOUNTRY',
    'HTTP_X_COUNTRY_CODE',
    'HTTP_X_GEOIP_COUNTRY_CODE',
    'HTTP_X_APPENGINE_COUNTRY',
    'HTTP_X_VERCEL_IP_COUNTRY',
)

UNKNOWN_COUNTRY_CODES = {'', 'XX', 'T1', 'A1', 'A2', 'O1', 'ZZ'}


def _normalize_country_code(value):
    if not value:
        return ''
    return str(value).split(',')[0].strip().upper()


def _language_for_country(country_code):
    if country_code in UNKNOWN_COUNTRY_CODES:
        return None
    if country_code == 'UA':
        return 'uk'
    return 'en'


def detect_initial_language(request):
    for header_name in COUNTRY_HEADER_CANDIDATES:
        language = _language_for_country(_normalize_country_code(request.META.get(header_name)))
        if language and check_for_language(language):
            return language

    default_language = settings.LANGUAGE_CODE
    if check_for_language(default_language):
        return default_language

    return None


class InitialLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = self._get_initial_language(request)
        if language:
            request.COOKIES[settings.LANGUAGE_COOKIE_NAME] = language

        response = self.get_response(request)

        if language:
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                language,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=getattr(settings, 'LANGUAGE_COOKIE_PATH', '/'),
                domain=getattr(settings, 'LANGUAGE_COOKIE_DOMAIN', None),
                secure=getattr(settings, 'LANGUAGE_COOKIE_SECURE', False),
                httponly=getattr(settings, 'LANGUAGE_COOKIE_HTTPONLY', False),
                samesite=getattr(settings, 'LANGUAGE_COOKIE_SAMESITE', None),
            )
            patch_vary_headers(response, ('Cookie',))

        return response

    def _get_initial_language(self, request):
        if request.path.startswith('/i18n/'):
            return None
        if request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME):
            return None
        return detect_initial_language(request)
