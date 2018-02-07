import datetime
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

    past_tournaments = Tournament.get_list_by_player(player=player, date_filter='past', type_filter='except_b')
    past_b_tournaments = Tournament.get_list_by_player(player=player, date_filter='past', type_filter='b')
    future_tournaments = Tournament.get_list_by_player(player=player, date_filter='future')
    past_away_tournaments = Tournament.get_list_by_player(player=player, date_filter='past', type_filter='away')

    today = datetime.datetime.now()
    current_year = today.year
    current_year = '2017'

    this_year_tournaments_count = past_tournaments.filter(start_date__year=current_year).count()
    this_year_b_tournaments_count = past_b_tournaments.filter(start_date__year=current_year).count()
    this_year_liga_tournaments_count = past_tournaments.filter(start_date__year=current_year).count()
    this_year_rating_tournaments_count = past_tournaments.filter(start_date__year=current_year,is_goes_to_rating=True).count()
    this_year_away_tournaments_count = past_away_tournaments.filter(start_date__year=current_year).count()

    player_summary_info = {
        'this_year_tournaments_count': this_year_tournaments_count,
        'this_year_b_tournaments_count': this_year_b_tournaments_count,
        'this_year_tournaments_count': this_year_liga_tournaments_count,
        'this_year_rating_tournaments_count': this_year_rating_tournaments_count,
        'this_year_away_tournaments_count': this_year_away_tournaments_count
    }

    return render(request, 'players/player.html', {
        'player': player,
        'player_summary_info': player_summary_info,
        'past_tournaments': past_tournaments,
        'future_tournaments': future_tournaments,
        'past_b_tournaments': past_b_tournaments,
        'past_away_tournaments': past_away_tournaments
    })