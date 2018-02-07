import datetime
from django.shortcuts import render
from django_bootstrap_carousel.models import Carousel
from federation.helpers.general import get_model

def main_page(request):
    carousel = Carousel.objects.get(pk=1)

    players_limit = 5

    players_model = get_model('Player')
    players_objects = players_model.get_actual_players_list()

    top_players = players_objects.order_by('-current_rating')[:players_limit]
    top_players_b = players_objects.order_by('-current_rating_b')[:players_limit]

    top_players_women = players_objects.filter(gender="F").order_by('-current_rating')[:players_limit]
    top_players_men = players_objects.filter(gender="M").order_by('-current_rating')[:players_limit]

    min_age = datetime.datetime.now() - datetime.timedelta(days=18 * 365)
    top_players_junior = players_objects.filter(birth_date__gte=min_age).order_by('-current_rating')[:players_limit]

    min_age = datetime.datetime.now() - datetime.timedelta(days=19 * 365)
    max_age = datetime.datetime.now() - datetime.timedelta(days=23 * 365)
    top_players_espoir = players_objects.filter(birth_date__lte=min_age, birth_date__gte=max_age).order_by('-current_rating')[:players_limit]

    min_age = datetime.datetime.now() - datetime.timedelta(days=24 * 365)
    max_age = datetime.datetime.now() - datetime.timedelta(days=55 * 365)
    top_players_senior = players_objects.filter(birth_date__lte=min_age, birth_date__gte=max_age).order_by('-current_rating')[:players_limit]

    min_age = datetime.datetime.now() - datetime.timedelta(days=56 * 365)
    top_players_veteran = players_objects.filter(birth_date__lte=min_age).order_by('-current_rating')[:players_limit]

    return render(request, 'main_page.html', {
        'carousel': carousel,
        'top_players': top_players,
        'top_players_b': top_players_b,
        'top_players_women': top_players_women,
        'top_players_men': top_players_men,
        'top_players_senior': top_players_senior,
        'top_players_junior': top_players_junior,
        'top_players_espoir': top_players_espoir,
        'top_players_veteran': top_players_veteran,
    })