from django.shortcuts import render
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from django.shortcuts import get_object_or_404


def tournaments(request, date_filter=None, type_filter=None):
    return render(request, 'tournaments/tournaments.html', {
        'tournaments': Tournament.get_list(date_filter=date_filter, type_filter=type_filter),
        'page_title': "Турніри",
    })


def tournament(request, id):
    tournament = get_object_or_404(Tournament, pk=id)
    arbiters = ArbiterTournamentMembership.objects.filter(tournament=tournament)
    teams = TeamTournamentMembership.objects.filter(tournament=tournament)

    return render(request, 'tournaments/tournament.html', {
        'tournament': tournament,
        'arbiters': arbiters,
        'teams': teams,
        'page_title': "Турнір",
    })

def tournaments_calendar (request):

    return render(request, 'tournaments/calendar.html')