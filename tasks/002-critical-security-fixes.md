# Task 002: Critical Security Fixes

## Goal

Fix actively exploitable vulnerabilities that allow unauthorized data modification or credential exposure.

## Why This Is Urgent

These issues can be exploited right now by anyone with access to the site:
- Tournament metadata can be modified by any anonymous visitor
- The settings context processor leaks all secrets (including AWS keys) to template context
- CSRF protection is completely disabled on state-changing tournament operations

## Scope

### Must Fix (Exploitable Now)

1. **Remove `@csrf_exempt` from tournament view** (`views/tournaments.py:29`)
   - Add CSRF token to AJAX calls that update meta
   - Ensure all tournament forms include `{% csrf_token %}`

2. **Add authentication check before `meta` update** (`views/tournaments.py:36-39`)
   - Move the `meta` handling below the `current_user.is_authenticated` check
   - Require `tournament.is_user_has_admin_access_to_tournament(current_user)`

3. **Replace settings context processor** (`federation/context_processors.py`)
   - Change from `{"settings": settings}` to only expose safe values:
     ```python
     def settings_context(request):
         return {
             "CURRENT_COUNTRY": settings.CURRENT_COUNTRY,
             "STATIC_URL": settings.STATIC_URL,
             "MEDIA_URL": settings.MEDIA_URL,
         }
     ```
   - Verify all templates that use `{{ settings.X }}` and replace with explicit context values

4. **Move `SECRET_KEY` to environment** (`api/settings.py:33`)
   - `SECRET_KEY = get_credential('secret_key')` or `os.environ['DJANGO_SECRET_KEY']`
   - Fail startup if not set
   - Generate a new key for production (the old one is compromised in git history)

5. **Move DB password to `.env`** (`docker-compose.yml:33-35`)
   - Reference `${POSTGRES_PASSWORD}` from env_file

### Should Fix (Same PR If Possible)

6. **Fix open redirect** (`views/login.py:31-35`)
   - Add `url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})`

7. **Fix error handlers** (`federation/urls.py:82-90`)
   - Remove deprecated `context_instance=RequestContext(request)` 
   - Use simple `render(request, '404.html', status=404)`

## Acceptance Criteria

- Anonymous users cannot modify tournament data (returns 403)
- CSRF protection is active on all POST endpoints
- `{{ settings.SECRET_KEY }}` in a template renders empty/error, not the actual key
- App fails to start if SECRET_KEY is not in environment
- Login redirect only goes to same-origin URLs
- 404/500 pages render without crashing

## Files To Modify

- `components/web-api/application/federation/views/tournaments.py`
- `components/web-api/application/federation/context_processors.py`
- `components/web-api/application/api/settings.py`
- `components/web-api/application/federation/views/login.py`
- `components/web-api/application/federation/urls.py`
- `docker-compose.yml`
- `.env.sample`
- Tournament templates that use AJAX (need CSRF header)

## Complexity

M

## Risk

High — touching auth/CSRF logic on active production views. Must verify tournament admin edit flows still work after changes.

## Big Win

High — closes the most severe security gaps.
