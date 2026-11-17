import re


_PHONE_USER_AGENT = re.compile(r'\b(?:Android.+Mobile|iPhone|iPod|Windows Phone|BlackBerry|Opera Mini)\b', re.I)


def is_phone_request(request):
    mobile_hint = request.headers.get('Sec-CH-UA-Mobile')
    if mobile_hint in ('?0', '?1'):
        return mobile_hint == '?1'

    return bool(_PHONE_USER_AGENT.search(request.headers.get('User-Agent', '')))
