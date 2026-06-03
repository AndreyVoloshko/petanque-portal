from django.shortcuts import render
from federation.models.player import Player
from federation.views.title_registry import (
    ROUTE_CONFIG,
    SPORT_TITLE_SHORT_LABELS,
    player_choice_groups,
    title_registry_context,
)


def sport_titles(request):
    groups = player_choice_groups(
        Player.SPORT_TITLES,
        'sport_title',
        SPORT_TITLE_SHORT_LABELS,
        ROUTE_CONFIG['sport_titles']['icon_class'],
    )

    return render(request, 'sport_titles/sport_titles.html', {
        **title_registry_context('sport_titles', groups),
    })
