from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from federation.models.player import Player
from federation.models.club import Club
from datetime import date


def tournaments_list(request):
    #start_date = parse_datetime(request.GET.get('start'))
    #end_date = parse_datetime(request.GET.get('end'))
    start_date = date(date.today().year, 1, 1)
    end_date = date(date.today().year + 1, 1, 1)
    data = []

    if start_date and end_date:

        tournaments = Tournament.get_list_by_dates_range(start_date, end_date)

        for tournament in tournaments:
            classes = "tournament "

            if tournament.is_goes_to_rating:
                classes += "tournament_goes_to_rating "

            if tournament.is_ukrainian_league:
                classes += "tournament_ukrainian_league "

            if tournament.is_b_tournament:
                classes += "tournament_b "

            classes += " tournament_" + str(tournament.category)

            item = {
                'id': tournament.pk,
                'url': reverse('tournament', kwargs={'id':tournament.pk}),
                'title': tournament.name,
                'start': tournament.start_date,
                'end': tournament.start_date,
                'className': classes,
                'allDay': True,
            }

            if tournament.end_date:
                item['end'] = tournament.end_date

            data.append(item)

    return JsonResponse(data, safe=False)


def players_clubs_and_tournaments_list(request):
    template = request.GET.get('typedText')
    data = []

    if template:
        players = Player.objects.filter(Q(name__icontains=template) | Q(surname__icontains=template))
        clubs = Club.objects.filter(name__icontains=template)
        tournaments = Tournament.objects.filter(name__icontains=template)

        for player in players:
            item = {
                'href': reverse('player', kwargs={'id':player.pk}),
                'value': player.get_name(),
                'disabled': 0,
            }

            data.append(item)

        for club in clubs:
            item = {
                'href': reverse('club', kwargs={'id':club.pk}),
                'value': club.name,
                'disabled': 0,
            }

            data.append(item)

        for tournament in tournaments:
            item = {
                'href': reverse('tournament', kwargs={'id':tournament.pk}),
                'value': tournament.name,
                'disabled': 0,
            }

            data.append(item)

    return JsonResponse(data, safe=False)


def players_list(request):
    template = request.GET.get('q')

    data = {
        "results": [],
        "pagination": {
            "more": False
        }
    }

    if template:
        players = Player.objects.filter(Q(name__icontains=template) | Q(surname__icontains=template))
        for player in players:
            item = {
                'id': player.pk,
                'text': player.get_name(),
            }

            data['results'].append(item)

    return JsonResponse(data, safe=False)