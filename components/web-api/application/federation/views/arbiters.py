from django.shortcuts import render
from federation.models.player import Player
from federation.views.title_registry import (
    ARBITER_SHORT_LABELS,
    ROUTE_CONFIG,
    player_choice_groups,
    title_registry_context,
)


def arbiters(request):
    groups = player_choice_groups(
        Player.ARBITER_CATEGORY,
        'arbiter_level',
        ARBITER_SHORT_LABELS,
        ROUTE_CONFIG['arbiters']['icon_class'],
    )

    return render(request, 'arbiters/arbiters.html', {
        **title_registry_context('arbiters', groups),
    })
