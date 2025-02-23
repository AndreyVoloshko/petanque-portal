from django.shortcuts import render
from federation.models.player import Player


def coaches(request):
    coaches_objects = []

    for category in reversed(Player.COACH_CATEGORY):
        players = Player.objects.filter(coach_level=category[0])

        if players:
            coaches_objects.append({
                'category_name': category[1],
                'category_id': category[0],
                'players': players
            })

    return render(request, 'coaches/coaches.html', {
        'coaches': coaches_objects,
        'page_title': "Тренери"
    })