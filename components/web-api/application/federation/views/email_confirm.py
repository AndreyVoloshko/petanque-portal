from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from federation.models.email_confirmation import EmailConfirmation
from federation.utils.email import send_confirmation_email


def _safe_next_url(request):
    next_url = request.POST.get('next') or request.GET.get('next') or reverse('profile')
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return reverse('profile')


class EmailPromptForm(forms.Form):
    email = forms.EmailField(
        label='Email адреса',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(EmailPromptForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        email_exists = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists()
        if email_exists:
            raise forms.ValidationError('Цей email вже використовується іншим користувачем.')
        return email


@login_required(login_url='/login/')
def email_prompt(request):
    next_url = _safe_next_url(request)
    if request.GET.get('skip'):
        return HttpResponseRedirect(next_url)

    initial_email = request.user.email
    pending_confirmation = None
    try:
        pending_confirmation = request.user.email_confirmation
        if not initial_email:
            initial_email = pending_confirmation.email
    except EmailConfirmation.DoesNotExist:
        pass

    form = EmailPromptForm(request.user, initial={'email': initial_email})
    if request.method == 'POST':
        form = EmailPromptForm(request.user, request.POST)
        if form.is_valid():
            EmailConfirmation.objects.filter(user=request.user).delete()
            confirmation = EmailConfirmation.objects.create(
                user=request.user,
                email=form.cleaned_data['email'],
            )
            send_confirmation_email(request, request.user, confirmation)
            messages.success(request, 'Лист надіслано! Перевірте пошту.', extra_tags='success')
            query = urlencode({'sent': '1', 'next': next_url})
            return HttpResponseRedirect('{}?{}'.format(reverse('email_prompt'), query))

    skip_url = '{}?{}'.format(reverse('email_prompt'), urlencode({'skip': '1', 'next': next_url}))
    return render(request, 'email_confirm/prompt.html', {
        'form': form,
        'next_url': next_url,
        'skip_url': skip_url,
        'sent': request.GET.get('sent'),
        'pending_confirmation': pending_confirmation,
    })


def email_confirm(request, token):
    try:
        confirmation = EmailConfirmation.objects.select_related('user').get(token=token, confirmed=False)
    except EmailConfirmation.DoesNotExist:
        return render(request, 'email_confirm/invalid.html')

    if confirmation.is_expired:
        return render(request, 'email_confirm/invalid.html')

    email_used = User.objects.filter(email__iexact=confirmation.email).exclude(pk=confirmation.user.pk).exists()
    if email_used:
        return render(request, 'email_confirm/invalid.html', {
            'error_message': 'Цей email вже використовується іншим користувачем.',
        })

    user = confirmation.user
    user.email = confirmation.email
    user.save(update_fields=['email'])

    confirmation.confirmed = True
    confirmation.confirmed_at = timezone.now()
    confirmation.save(update_fields=['confirmed', 'confirmed_at'])

    return render(request, 'email_confirm/success.html', {
        'confirmation': confirmation,
    })
