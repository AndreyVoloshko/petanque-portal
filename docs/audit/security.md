# Security Audit

## Summary

Security is the most urgent category. The app has multiple high-impact vulnerabilities that should be addressed before any other work. Several issues were found beyond the original audit scope.

## Critical Findings

### 1. Hardcoded Django Secret Key

**File:** `components/web-api/application/api/settings.py:33`

```python
SECRET_KEY = 'k1n!-r2wazl!q#2dn3wa9_lm5v2))#n-k8veqn_u@+^0-@4m$w'
```

Impact: session hijacking, password reset token forgery, CSRF token forgery. This key has been committed to version control and should be considered compromised.

Recommendation: rotate the key immediately, move to environment variable, fail startup if absent.

### 2. CSRF Disabled On Tournament Detail View + Unauthenticated Mutation

**File:** `components/web-api/application/federation/views/tournaments.py:29-38`

```python
@csrf_exempt
def tournament(request, id):
    ...
    if request.method == "POST":
        if 'meta' in request.POST:
            tournament.meta = request.POST['meta']
            tournament.save()
            return JsonResponse({'status': 'ok'}, safe=False)
```

The `meta` update happens before any authentication check. Lines 48-76 check auth but lines 36-39 do not.

Impact: any anonymous user or CSRF attacker can modify tournament metadata.

### 3. Settings Context Processor Leaks All Settings To Templates

**File:** `components/web-api/application/federation/context_processors.py`

```python
def settings_context(request):
    return {"settings": settings}
```

This exposes `SECRET_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, database credentials, and all other settings to every template context. If any template accidentally renders `{{ settings }}` or a debug page leaks context, all secrets are exposed.

Impact: complete credential exposure via template debugging, error pages, or XSS.

Recommendation: replace with explicit safe values only (e.g., `CURRENT_COUNTRY`, `STATIC_URL`).

### 4. Database Password Hardcoded in docker-compose.yml

**File:** `docker-compose.yml:33-35`

```yaml
environment:
  POSTGRES_PASSWORD: petanque_portal_db_password
  POSTGRES_USER: postgres
```

Impact: database credentials exposed in version control.

### 5. Open Redirect On Login

**File:** `components/web-api/application/federation/views/login.py:31-35`

```python
next_url = '/profile/'
if request.POST.get('next', ''):
    next_url = request.POST.get('next', '')
return HttpResponseRedirect(next_url)
```

No validation of `next_url`. An attacker can redirect authenticated users to phishing sites.

Recommendation: use `django.utils.http.url_has_allowed_host_and_scheme()`.

### 6. Global CORS Allow-All

**File:** `components/web-api/application/api/settings.py:234-236`

```python
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_METHODS = ['GET']
```

Less severe because only GET is allowed, but still permits data scraping from arbitrary origins. Combined with the search API endpoints that return player data, this is a privacy concern.

### 7. Stored XSS Via Template Filters

**File:** `components/web-api/application/federation/templatetags/app_filters.py`

Multiple filters build HTML via string concatenation with database values:

- `social_field()` (line 154-166): `'<a target="_blank" href="' + value + '"...'` — URL from DB field
- `country_icon()` (line 53-58): `country.code` injected into class name without escaping
- `club_logo()` (line 68-80): `club.id` and `url` concatenated into HTML
- `user_profile_link()` (line 108-116): player name inserted without escaping
- `tournament_field()` (line 346-381): `value` from various DB fields rendered directly
- `player_age_category()` (line 169-186): returns raw HTML badges

These are rendered in templates with `|safe` (178 total usages across templates).

Impact: if any admin-editable field contains JavaScript (social URLs, player names, tournament places, club names, record descriptions), it executes in visitors' browsers.

### 8. Weak Password Generation

**File:** `components/web-api/application/federation/views/register.py:50`

```python
password = player_registration_form.cleaned_data['surname']+str(datetime.datetime.now())
```

Passwords are predictable (surname + precise timestamp). The password is never communicated to the user in a useful way.

### 9. CAPTCHA Disabled On Team Registration

**File:** `components/web-api/application/federation/forms/registration_team_form.py:35-37`

CAPTCHA field is commented out, allowing automated mass registration.

### 10. Silk Profiler Unconditionally Installed

**File:** `components/web-api/application/api/settings.py:61`

`django-silk` is in `INSTALLED_APPS` without being gated behind `DEBUG`. If silk's URL patterns are mounted (not currently, but any future inclusion), it would expose query profiling data in production.

Even without URL mounting, silk's middleware intercepts may be active and could cause overhead or data collection.

## High-Risk Findings

### 11. Missing Session Security Headers

No cookie security settings defined. Missing:

```python
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
```

### 12. No Rate Limiting On API Endpoints

**File:** `components/web-api/application/federation/views/api.py`

Three public JSON endpoints with no authentication or rate limiting:
- `/api/tournaments/list/` — returns all tournament data in date range
- `/api/players_clubs_and_tournaments/list/` — unbounded search with no pagination
- `/api/players_list/list/` — player search, no pagination

Impact: data scraping, enumeration, DoS via expensive queries.

### 13. File Upload Validation Disconnected

**File:** `components/web-api/application/federation/forms/player_form.py`

`clean_content()` validates a field called `content`, but the actual field is `avatar`. The validation never executes.

### 14. Registration Creates Accounts Without Email Verification

**File:** `components/web-api/application/federation/views/register.py:47-65`

Player registration creates Django User accounts without email verification. Combined with disabled CAPTCHA, allows mass account creation.

### 15. DATA_UPLOAD_MAX_NUMBER_FIELDS Too High

**File:** `components/web-api/application/api/settings.py:231`

```python
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240
```

Default is 1000. 10240 enables potential slow POST parsing attacks.

## Medium-Risk Findings

### 16. Debug/Environment Configuration Not Validated

Critical values from `APP_CREDENTIALS` can silently become `None`:
- `ALLOWED_HOSTS = get_credential('domains')` — if None, Django in non-DEBUG mode rejects all requests
- `CSRF_TRUSTED_ORIGINS = get_credential('csrf_origins')` — if None, can break CSRF validation
- `DATABASES['default']` values — if None, app crashes on first query

### 17. Bare `except:` in Settings

**File:** `components/web-api/application/api/settings.py:18`

```python
try:
    credentials = json.loads(os.environ.get('APP_CREDENTIALS', '{}'))
except:
    credentials = {}
```

Silently swallows JSON parse errors, leading to all credentials returning None.

### 18. `STATIC_ROOT = STATIC_URL` Misconfiguration

**File:** `components/web-api/application/api/settings.py:206`

```python
STATIC_ROOT = STATIC_URL
```

`STATIC_ROOT` should be a filesystem path, not a URL. This breaks `collectstatic` and may cause issues with Django's static file system checks.

## Security Priority (Revised)

Fix in this order:

1. Remove `@csrf_exempt` and add auth check before `meta` mutation.
2. Replace settings context processor with explicit safe values.
3. Move `SECRET_KEY` to environment and rotate.
4. Move DB password to environment variable.
5. Fix open redirect.
6. Add session/cookie security headers.
7. Convert `|safe` filters to `format_html()`.
8. Lock down CORS to specific origins.
9. Re-enable CAPTCHA or add rate limiting.
10. Fix file upload validation.
