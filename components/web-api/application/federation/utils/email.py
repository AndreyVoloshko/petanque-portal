from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags


def send_confirmation_email(request, user, confirmation):
    confirm_url = request.build_absolute_uri(
        reverse('email_confirm', kwargs={'token': confirmation.token})
    )
    subject = render_to_string('email_confirm/email_subject.txt').strip()
    html_body = render_to_string('email_confirm/email_body.html', {
        'user': user,
        'confirmation': confirmation,
        'confirm_url': confirm_url,
    })
    send_mail(
        subject,
        strip_tags(html_body),
        None,
        [confirmation.email],
        html_message=html_body,
    )
