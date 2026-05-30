import datetime
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from federation.models.player import Player
from federation.models.tournament import Tournament
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from federation.helpers.general import get_model


def players(request, licence_filter=None, rating_filter=None):

    players_objects = Player.objects.all()
    if licence_filter == 'licence':
        players_objects = Player.get_actual_players_list()
    elif licence_filter == 'inclusive':
        players_objects = Player.objects.filter(is_inclusive=True)

    rating_field = 'current_rating'
    rating_power_field = 'current_power'
    if rating_filter == 'b':
        rating_field = 'current_rating_b'
        rating_power_field = 'current_power_b'
    elif rating_filter == 'liga':
        rating_field = 'current_rating_liga'
    elif rating_filter == 'inclusive':
        rating_field = 'current_rating_inclusive'
        rating_power_field = 'current_power_inclusive'

    return render(request, 'players/players.html', {
        'players': players_objects,
        'rating_filters': rating_field+","+str(licence_filter),
        'rating_field': rating_field,
        'rating_power_field': rating_power_field,
        'page_title': _("Athletes"),
    })


def player(request, id):
    player = get_object_or_404(Player, pk=id)

    past_tournaments = Tournament.get_list_by_player(player=player, date_filter='past', type_filter='except_b')
    past_b_tournaments = Tournament.get_list_by_player(player=player, date_filter='past', type_filter='b')
    future_tournaments = Tournament.get_list_by_player(player=player, date_filter='future')
    past_away_tournaments = Tournament.get_list_by_player(player=player, date_filter='past', type_filter='away')

    today = datetime.datetime.now()
    current_year = today.year

    this_year_tournaments_count = past_tournaments.filter(start_date__year=current_year).count()
    this_year_b_tournaments_count = past_b_tournaments.filter(start_date__year=current_year).count()
    this_year_liga_tournaments_count = past_tournaments.filter(start_date__year=current_year).count()
    this_year_rating_tournaments_count = past_tournaments.filter(start_date__year=current_year, is_goes_to_rating=True).count()
    this_year_away_tournaments_count = past_away_tournaments.filter(start_date__year=current_year).count()

    player_summary_info = {
        'this_year_tournaments_count': this_year_tournaments_count,
        'this_year_b_tournaments_count': this_year_b_tournaments_count,
        'this_year_liga_tournaments_count': this_year_liga_tournaments_count,
        'this_year_rating_tournaments_count': this_year_rating_tournaments_count,
        'this_year_away_tournaments_count': this_year_away_tournaments_count,
    }

    recent_tournaments = list(past_tournaments.order_by('-start_date')[:6])

    season_rating_field = "rating"
    seasons_model = get_model('Season')
    player_seasons = seasons_model.objects.filter(player=player).order_by('-year')

    from federation.models.national_teams import PlayerNational_teamMembership
    national_team_memberships = PlayerNational_teamMembership.objects.filter(player=player).select_related('team')

    return render(request, 'players/player.html', {
        'player': player,
        'player_summary_info': player_summary_info,
        'past_tournaments': past_tournaments,
        'future_tournaments': future_tournaments,
        'past_b_tournaments': past_b_tournaments,
        'past_away_tournaments': past_away_tournaments,
        'recent_tournaments': recent_tournaments,
        'national_team_memberships': national_team_memberships,
        'season_rating_field': season_rating_field,
        'player_seasons': player_seasons,
    })
