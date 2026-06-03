from django.shortcuts import render
from federation.models.player import Player
from federation.views.title_registry import (
    COACH_SHORT_LABELS,
    ROUTE_CONFIG,
    player_choice_groups,
    title_registry_context,
)


def coaches(request):
    groups = player_choice_groups(
        Player.COACH_CATEGORY,
        'coach_level',
        COACH_SHORT_LABELS,
        ROUTE_CONFIG['coaches']['icon_class'],
    )

    return render(request, 'coaches/coaches.html', {
        **title_registry_context('coaches', groups),
    })
