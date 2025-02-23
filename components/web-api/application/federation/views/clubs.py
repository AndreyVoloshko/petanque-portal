from django.shortcuts import render
from django.shortcuts import get_object_or_404
from federation.models.club import Club
from federation.models.player import Player


def clubs(request):
    return render(request, 'clubs/clubs.html', {
        'clubs': Club.objects.all(),
        'page_title': "Клуби"
    })

def club(request, id):
    club = get_object_or_404(Club, pk=id)
    players = Player.objects.filter(current_club=club)

    rating_field = 'current_rating'
    rating_power_field = 'current_power'
    licence_filter = 'license'

    return render(request, 'clubs/club.html', {
        'club': club,
        'rating_field': rating_field,
        'rating_power_field': rating_power_field,
        'rating_filters': rating_field + "," + str(licence_filter),
        'players': players
    })