from django.shortcuts import render
from federation.models.record import Record


def records(request):
    return render(request, 'records/records.html', {
        'records': Record.objects.all(),
        'page_title': "Рекорди України",
    })