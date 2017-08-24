from django.shortcuts import render
from django.shortcuts import get_object_or_404
from federation.models.player import Player

def players(request):
    return render(request, 'players/players.html', {
        'players': Player.objects.all(),
        'page_title': "Гравці",
    })

def player(request, id):
    player = get_object_or_404(Player, pk=id)

    return render(request, 'players/player.html', {
        'player': player
    })