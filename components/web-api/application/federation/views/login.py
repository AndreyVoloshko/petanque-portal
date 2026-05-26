from urllib.parse import urlencode

from django.shortcuts import render
from django.http import *
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from federation.models.email_confirmation import EmailConfirmation


def _safe_next_url(request):
    next_url = request.POST.get('next') or '/profile/'
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return '/profile/'


def _sync_existing_email_confirmation(user):
    if not user.email:
        return False

    try:
        confirmation = user.email_confirmation
    except EmailConfirmation.DoesNotExist:
        EmailConfirmation.objects.create(
            user=user,
            email=user.email,
            confirmed=True,
            confirmed_at=timezone.now(),
        )
        return False

    if confirmation.confirmed:
        if confirmation.email.lower() != user.email.lower():
            confirmation.email = user.email
            confirmation.confirmed_at = timezone.now()
            confirmation.save(update_fields=['email', 'confirmed_at'])
        return False

    return True


def _needs_email_prompt(user):
    return _sync_existing_email_confirmation(user)


def application_login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/profile/')

    if request.POST:
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is None:
            #
            # try to login using email
            #
            try:
                user_object = User.objects.get(email__iexact=username)
            except User.DoesNotExist:
                user_object = None
                
            if user_object is not None:
                user = authenticate(request, username=user_object.username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)

                next_url = _safe_next_url(request)
                if _needs_email_prompt(user):
                    email_prompt_url = '{}?{}'.format(
                        reverse('email_prompt'),
                        urlencode({'next': next_url}),
                    )
                    return HttpResponseRedirect(email_prompt_url)

                return HttpResponseRedirect(next_url)

    next = request.GET.get('next', '')

    return render(request, 'login.html', {
        'next': next
    })
