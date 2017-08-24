from django.shortcuts import render
from django.shortcuts import get_object_or_404
from federation.models.club import Club
from federation.models.player import Player

def clubs(request):
    return render(request, 'clubs/clubs.html', {
        'clubs': Club.objects.all(),
        'page_title': "Клуби ФПУ",
        'clubs_per_row': 2,
    })

def club(request, id):
    club = get_object_or_404(Club, pk=id)
    players = Player.objects.filter(current_club=club)

    return render(request, 'clubs/club.html', {
        'club': club,
        'players': players
    })