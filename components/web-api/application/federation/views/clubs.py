from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q, Sum
from django.utils.translation import gettext_lazy as _
from federation.models.club import Club
from federation.models.national_teams import PlayerNational_teamMembership
from federation.models.player import Player


def clubs(request):
    return render(request, 'clubs/clubs.html', {
        'clubs': Club.objects.all(),
        'page_title': _("Clubs")
    })

def club(request, id):
    club = get_object_or_404(Club.objects.select_related('city', 'president'), pk=id)
    players = (
        Player.objects
        .filter(current_club=club)
        .select_related('current_club')
        .order_by('-current_rating', 'surname', 'name')
    )
    licensed_players = (
        players
        .filter(is_licence_active=True)
        .exclude(licence_number__isnull=True)
        .exclude(licence_number='')
    )

    rating_field = 'current_rating'
    rating_power_field = 'current_power'
    licence_filter = 'licence'

    rating_stats = licensed_players.aggregate(
        total_rating=Sum('current_rating'),
        average_rating=Avg('current_rating'),
        average_power=Avg('current_power'),
        candidates_count=Count('id', filter=Q(sport_title='candidate')),
    )
    total_rating = rating_stats['total_rating'] or 0
    licensed_club_player_filter = (
        Q(player__is_licence_active=True)
        & ~Q(player__licence_number__isnull=True)
        & ~Q(player__licence_number='')
    )
    club_rank = (
        Club.objects
        .annotate(total_rating=Sum('player__current_rating', filter=licensed_club_player_filter))
        .filter(total_rating__gt=total_rating)
        .count()
        + 1
    )
    national_team_players_count = (
        PlayerNational_teamMembership.objects
        .filter(player__current_club=club)
        .values('player_id')
        .distinct()
        .count()
    )
    club_stats = {
        'players_count': players.count(),
        'licensed_players_count': licensed_players.count(),
        'total_rating': total_rating,
        'average_rating': rating_stats['average_rating'] or 0,
        'average_power': rating_stats['average_power'] or 0,
        'club_rank': club_rank,
        'national_team_players_count': national_team_players_count,
        'candidates_count': rating_stats['candidates_count'] or 0,
    }

    return render(request, 'clubs/club.html', {
        'club': club,
        'club_stats': club_stats,
        'rating_field': rating_field,
        'rating_power_field': rating_power_field,
        'rating_filters': rating_field + "," + str(licence_filter),
        'players': players
    })
