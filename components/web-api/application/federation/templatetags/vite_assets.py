import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin

from django import template
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.html import format_html

register = template.Library()


@lru_cache(maxsize=1)
def _manifest():
    path = Path(settings.BASE_DIR) / "static" / "vite" / "manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ImproperlyConfigured("Run npm ci and npm run build in components/web-api/frontend.") from exc


@register.simple_tag
def vite_stylesheet(entry):
    # collectstatic copies these files as is; Vite already fingerprints them.
    asset = _manifest()[entry]["file"]
    return format_html('<link rel="stylesheet" href="{}">', urljoin(settings.STATIC_URL, f"vite/{asset}"))
