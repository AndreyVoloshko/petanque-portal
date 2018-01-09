from django.http import JsonResponse
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership

def tournaments_list(request):
    start_date = parse_datetime(request.GET.get('start'))
    end_date = parse_datetime(request.GET.get('end'))

    tournaments = Tournament.get_list_by_dates_range(start_date, end_date)
    data = []

    for tournament in tournaments:
        item = {
            'id': tournament.pk,
            'url': reverse('tournament', kwargs={'id':tournament.pk}),
            'title': tournament.name,
            'start': tournament.start_date,
            'end': tournament.start_date,
            'allDay': True,
        }

        if tournament.end_date:
            item['end'] = tournament.end_date

        data.append(item)

    return JsonResponse(data, safe=False)