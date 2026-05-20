from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from federation.models.player import Player


def sport_titles(request):
    players_objects = []

    for category in reversed(Player.SPORT_TITLES):
        players = Player.objects.filter(sport_title=category[0])

        if players:
            players_objects.append({
                'category_name': category[1],
                'category_id': category[0],
                'players': players
            })

    return render(request, 'sport_titles/sport_titles.html', {
        'arbiters': players_objects,
        'page_title': _("Sports titles")
    })
