import datetime
from django.shortcuts import render
from federation.helpers.general import get_model

def main_page(request):

    items_limit = 3

    players_model = get_model('Player')
    players_objects = players_model.get_actual_players_list()

    tournaments_model = get_model('Tournament')

    top_players = players_objects.order_by('-current_rating')[:items_limit]
    top_players_b = players_objects.order_by('-current_rating_b')[:items_limit]

    top_players_women = players_objects.filter(gender="F").order_by('-current_rating')[:items_limit]
    top_players_men = players_objects.filter(gender="M").order_by('-current_rating')[:items_limit]

    # min_age = datetime.datetime.now() - datetime.timedelta(days=18 * 365)
    # top_players_junior = players_objects.filter(birth_date__gte=min_age).order_by('-current_rating')[:items_limit]

    # min_age = datetime.datetime.now() - datetime.timedelta(days=19 * 365)
    # max_age = datetime.datetime.now() - datetime.timedelta(days=23 * 365)
    # top_players_espoir = players_objects.filter(birth_date__lte=min_age, birth_date__gte=max_age).order_by('-current_rating')[:items_limit]
    
    min_age = datetime.datetime.now() - datetime.timedelta(days=23 * 365)
    top_players_espoir_and_junior = players_objects.filter(birth_date__gte=min_age).order_by('-current_rating')[:items_limit]

    min_age = datetime.datetime.now() - datetime.timedelta(days=24 * 365)
    max_age = datetime.datetime.now() - datetime.timedelta(days=55 * 365)
    top_players_senior = players_objects.filter(birth_date__lte=min_age, birth_date__gte=max_age).order_by('-current_rating')[:items_limit]

    min_age = datetime.datetime.now() - datetime.timedelta(days=56 * 365)
    top_players_veteran = players_objects.filter(birth_date__lte=min_age).order_by('-current_rating')[:items_limit]

    # tournament lists
    items_limit = 12
    future_tournaments_rating = tournaments_model.get_list(date_filter='future', type_filter='rating')[:items_limit]
    future_tournaments_away = tournaments_model.get_list(date_filter='future', type_filter='away')[:items_limit]
    future_tournaments = tournaments_model.get_list(date_filter='future', type_filter='non_rating')[:items_limit]

    # past_tournaments_rating = tournaments_model.get_list(date_filter='past', type_filter='rating')[:items_limit]
    # past_tournaments_away = tournaments_model.get_list(date_filter='past', type_filter='away')[:items_limit]
    # past_tournaments = tournaments_model.get_list(date_filter='past', type_filter='non_rating')[:items_limit]

    return render(request, 'main_page.html', {
        #'carousel': carousel,
        'top_players': top_players,
        'top_players_b': top_players_b,
        'top_players_women': top_players_women,
        'top_players_men': top_players_men,
        'top_players_senior': top_players_senior,
        # 'top_players_junior': top_players_junior,
        # 'top_players_espoir': top_players_espoir,
        'top_players_espoir_and_junior': top_players_espoir_and_junior,
        'top_players_veteran': top_players_veteran,

        'future_tournaments_rating': future_tournaments_rating,
        'future_tournaments_away': future_tournaments_away,
        'future_tournaments': future_tournaments,
        # 'past_tournaments_rating': past_tournaments_rating,
        # 'past_tournaments_away': past_tournaments_away,
        # 'past_tournaments': past_tournaments

    })
