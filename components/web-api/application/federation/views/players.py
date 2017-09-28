from django.shortcuts import render
from django.shortcuts import get_object_or_404
from federation.models.player import Player
from federation.models.tournament import Tournament

def players(request):
    return render(request, 'players/players.html', {
        'players': Player.objects.all(),
        'page_title': "Гравці",
    })

def player(request, id):
    player = get_object_or_404(Player, pk=id)

    return render(request, 'players/player.html', {
        'player': player,
        'past_tournaments': Tournament.get_list_by_player(player=player, date_filter='past', type_filter='except_b'),
        'future_tournaments': Tournament.get_list_by_player(player=player, date_filter='future'),
        'past_b_tournaments': Tournament.get_list_by_player(player=player, date_filter='past', type_filter='b')
    })