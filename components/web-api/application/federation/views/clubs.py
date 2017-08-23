from django.shortcuts import render
from federation.models.club import Club

def clubs(request):
    return render(request, 'clubs.html', {
        'clubs': Club.objects.all(),
        'page_title': "Клуби ФПУ",
        'clubs_per_row': 2,
    })