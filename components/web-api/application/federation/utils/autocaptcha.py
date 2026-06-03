import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'
DEFAULT_ACTION = 'player_registration'
DEFAULT_SCORE_THRESHOLD = 0.5
REQUEST_TIMEOUT_SECONDS = 5


def get_public_key():
    return getattr(settings, 'RECAPTCHA_PUBLIC_KEY', None)


def is_configured():
    return bool(get_public_key() and getattr(settings, 'RECAPTCHA_PRIVATE_KEY', None))


def _get_score_threshold():
    raw_threshold = getattr(settings, 'AUTO_CAPTCHA_SCORE_THRESHOLD', DEFAULT_SCORE_THRESHOLD)
    try:
        return float(raw_threshold)
    except (TypeError, ValueError):
        return DEFAULT_SCORE_THRESHOLD


def _is_debug_without_keys():
    return bool(getattr(settings, 'DEBUG', False)) and not is_configured()


def validate_autocaptcha(token, remote_ip=None, expected_action=DEFAULT_ACTION):
    if _is_debug_without_keys():
        return

    private_key = getattr(settings, 'RECAPTCHA_PRIVATE_KEY', None)
    if not private_key or not get_public_key():
        raise ValidationError(
            _('Automatic verification is unavailable. Please try again later.'),
            code='autocaptcha_unavailable',
        )

    if not token:
        raise ValidationError(
            _('Automatic verification failed. Please reload the page and try again.'),
            code='autocaptcha_missing',
        )

    payload = {
        'secret': private_key,
        'response': token,
    }
    if remote_ip:
        payload['remoteip'] = remote_ip

    request = Request(
        VERIFY_URL,
        data=urlencode(payload).encode('utf-8'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        raise ValidationError(
            _('Automatic verification failed. Please try again later.'),
            code='autocaptcha_error',
        )

    if not result.get('success'):
        raise ValidationError(
            _('Automatic verification failed. Please reload the page and try again.'),
            code='autocaptcha_failed',
        )

    if result.get('action') != expected_action:
        raise ValidationError(
            _('Automatic verification failed. Please reload the page and try again.'),
            code='autocaptcha_action',
        )

    try:
        score = float(result.get('score'))
    except (TypeError, ValueError):
        raise ValidationError(
            _('Automatic verification failed. Please reload the page and try again.'),
            code='autocaptcha_score_missing',
        )

    if score < _get_score_threshold():
        raise ValidationError(
            _('Automatic verification rejected this registration. Please try again later.'),
            code='autocaptcha_low_score',
        )
