from django.shortcuts import render
from federation.models.player import Player


def arbiters(request):
    arbiter_objects = []

    for category in reversed(Player.ARBITER_CATEGORY):
        players = Player.objects.filter(arbiter_level=category[0])

        if players:
            arbiter_objects.append({
                'category_name': category[1],
                'category_id': category[0],
                'players': players
            })

    return render(request, 'arbiters/arbiters.html', {
        'arbiters': arbiter_objects,
        'page_title': "Арбiтри"
    })