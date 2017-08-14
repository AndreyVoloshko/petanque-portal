from django import template
from django.conf import settings

register = template.Library()


@register.filter(name='user_avatar')
def user_avatar(user):
    return settings.MEDIA_URL + str(user.avatar)


@register.filter(name='user_field')
def user_field(value):
    if value == None:
        return ''
    return value


@register.filter(name='format_date')
def format_date(value):
    return value.strftime('%d.%m.%Y')