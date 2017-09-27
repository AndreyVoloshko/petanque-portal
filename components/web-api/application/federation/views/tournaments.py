from django.shortcuts import render
from federation.models.tournament import Tournament
import datetime


def tournaments(request, date_filter=None, type_filter=None):
    now = datetime.datetime.now()

    tournaments = Tournament.objects.all()

    if date_filter == 'past':
        tournaments.filter(start_date__year=now.year)
        tournaments.filter(start_date__lte=now)
    elif date_filter == 'future':
        tournaments.filter(start_date__gte=now)

    if type_filter == 'rating':
        tournaments.filter(is_goes_to_rating=True)
    elif type_filter == 'away':
        tournaments.filter(category='away')
    elif type_filter == 'b':
        tournaments.filter(is_b_tournament=True)
    elif type_filter == 'non':
        tournaments.filter(is_goes_to_rating=False)
        tournaments.filter(is_b_tournament=False)

    return render(request, 'tournaments/tournaments.html', {
        'tournaments': tournaments,
        'page_title': "Турніри",
    })

def tournament(request, id):
    tournaments = Tournament.objects.all()

    return render(request, 'tournaments/tournaments.html', {
        'tournaments': tournaments,
        'page_title': "Турніри",
    })