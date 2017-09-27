from django.shortcuts import render
from federation.models.player import Player

def arbiters(request):
    arbiter_objects = {}
    for category in reversed(Player.ARBITER_CATEGORY):
        players = Player.objects.filter(arbiter_level=category[0])
        if players:
            arbiter_objects[category[1]] = players

    return render(request, 'arbiters/arbiters.html', {
        'arbiters_by_levels': arbiter_objects,
        'page_title': "Арбiтри ФПУ",
        'items_per_row': 3
    })