from django.shortcuts import render
import datetime
from django.utils.translation import gettext_lazy as _
from federation.helpers.general import get_model


def seasons(request, year=None):
    seasons_model = get_model('Season')

    rating_field = "rating"

    if year is None:
        today = datetime.datetime.now()
        current_year = today.year
        year = current_year - 1

    players = seasons_model.objects.filter(year=year)

    years = []
    years_objects = seasons_model.objects.order_by('-year').values('year').distinct()
    for years_object in years_objects:
        years.append(str(years_object['year']))

    return render(request, 'seasons/seasons.html', {
        'players': players,
        'years': years,
        'year': str(year),
        'rating_field': rating_field,
        'rating_filters': rating_field+","+str(year),
        'page_title': _("Ranking for previous seasons"),
    })
