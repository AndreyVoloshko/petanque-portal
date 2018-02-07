from django.shortcuts import render
from django.shortcuts import get_object_or_404
from federation.models.player import Player
from federation.models.tournament import Tournament
from django.conf import settings


def players(request, licence_filter=None, rating_filter=None):

    players_objects = Player.objects.filter(country=settings.CURRENT_COUNTRY)
    if licence_filter == 'licence':
        players_objects = players_objects.exclude(licence_number="").exclude(licence_number__isnull=True)

    rating_field='current_rating'
    if rating_filter == 'b':
        rating_field = 'current_rating_b'
    elif rating_filter == 'liga':
        rating_field = 'current_rating_liga'

    return render(request, 'players/players.html', {
        'players': players_objects,
        'rating_filters': rating_field+","+str(licence_filter),
        'rating_field': rating_field,
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