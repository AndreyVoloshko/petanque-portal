from django.shortcuts import render
from federation.models.tournament import Tournament


def tournaments(request, date_filter=None, type_filter=None):
    return render(request, 'tournaments/tournaments.html', {
        'tournaments': Tournament.get_list(date_filter=date_filter, type_filter=type_filter),
        'page_title': "Турніри",
    })


def tournament(request, id):
    return render(request, 'tournaments/tournaments.html', {
        'tournaments': Tournament.get_list(),
        'page_title': "Турніри",
    })