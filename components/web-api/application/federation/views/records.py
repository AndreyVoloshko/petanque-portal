from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from federation.models.record import Record


def records(request):
    return render(request, 'records/records.html', {
        'records': Record.objects.all(),
        'page_title': _("Ukrainian records"),
    })
