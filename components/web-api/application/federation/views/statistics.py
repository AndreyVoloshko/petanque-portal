from operator import itemgetter
from collections import OrderedDict

from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.conf import settings

from federation.helpers.general import get_model


def statistics(request, year=None):
    tournament_model = get_model('Tournament')
    player_model = get_model('Player')
    season_model = get_model('Season')

    periods = []
    periods_all = tournament_model.objects.all().dates('start_date', 'year', order='DESC')
    for period in periods_all:
        periods.append({
            'year': str(period.year),
            'title': str(period.year) + ' рік'
        })

    tournaments_all = tournament_model.objects.all()
    if year is not None:
        tournaments_all = tournament_model.objects.filter(start_date__year=year).order_by('-start_date')

    tournaments_data = {
        'countries': {},
        'clubs': {},
        'organizers': {},
        'ua_places': {},
        'foreign_places': {},
        'ua_disciplines': {},
        'foreign_disciplines': {},
        'ua_teams_count': [],
        'foreign_teams_count': [],
        'ua_players_count': [],
        'foreign_players_count': [],
        'ua_biggest_tournament': {},
        'foreign_biggest_tournament': {},
        'ua_biggest_tournament_players': {},
        'foreign_biggest_tournament_players': {}
    }

    ua_biggest_teams_count = 0
    foreign_biggest_teams_count = 0

    ua_biggest_players_count = 0
    foreign_biggest_players_count = 0

    for tournament in tournaments_all:
        attibute_prefix = 'foreign_'
        if tournament.country == settings.CURRENT_COUNTRY:
            attibute_prefix = 'ua_'

            teams_count = int(tournament.get_teams_count())

            if teams_count > ua_biggest_teams_count:
                ua_biggest_teams_count = teams_count
                tournaments_data['ua_biggest_tournament'] = tournament

            if (teams_count * tournament.number_of_players_in_team_min) > ua_biggest_players_count:
                ua_biggest_players_count = (teams_count * tournament.number_of_players_in_team_min)
                tournaments_data['ua_biggest_tournament_players'] = tournament
                tournaments_data['ua_biggest_tournament_players_count'] = (teams_count * int(tournament.number_of_players_in_team_min))

        else:

            teams_count = int(tournament.get_teams_count())

            if teams_count > foreign_biggest_teams_count:
                foreign_biggest_teams_count = teams_count
                tournaments_data['foreign_biggest_tournament'] = tournament

            if (teams_count * tournament.number_of_players_in_team_min) > foreign_biggest_players_count:
                foreign_biggest_players_count = (teams_count * tournament.number_of_players_in_team_min)
                tournaments_data['foreign_biggest_tournament_players'] = tournament
                tournaments_data['foreign_biggest_tournament_players_count'] = (teams_count * int(tournament.number_of_players_in_team_min))

        # countries
        if tournament.country.code not in tournaments_data['countries']:
            tournaments_data['countries'][tournament.country.code] = {
                'country': tournament.country,
                'count': 0,
                'teams': 0
            }

        tournaments_data['countries'][tournament.country.code]['count'] += 1
        tournaments_data['countries'][tournament.country.code]['teams'] += tournament.get_teams().count()

        # clubs
        if tournament.organizer_club is not None and tournament.organizer_club.pk not in tournaments_data['clubs']:
            tournaments_data['clubs'][tournament.organizer_club.pk] = {
                'club': tournament.organizer_club,
                'count': 0
            }

        # organizers
        if tournament.main_organizer is not None and tournament.main_organizer.pk not in tournaments_data['organizers']:
            tournaments_data['organizers'][tournament.main_organizer.pk] = {
                'player': tournament.main_organizer,
                'count': 0
            }

        if tournament.main_organizer is not None:
            tournaments_data['organizers'][tournament.main_organizer.pk]['count'] += 1

        # places
        attibute = attibute_prefix + 'places'
        if tournament.place not in tournaments_data[attibute]:
            tournaments_data[attibute][tournament.place] = 0
        tournaments_data[attibute][tournament.place] += 1

        # disciplines
        attibute = attibute_prefix + 'disciplines'
        if tournament.number_of_players_in_team_min not in tournaments_data[attibute]:
            tournaments_data[attibute][tournament.number_of_players_in_team_min] = 0
        tournaments_data[attibute][tournament.number_of_players_in_team_min] += 1

        # teams
        attibute = attibute_prefix + 'teams_count'
        tournaments_data[attibute].append(tournament.get_teams_count())

        attibute = attibute_prefix + 'players_count'
        tournaments_data[attibute].append(tournament.get_teams_count() * tournament.number_of_players_in_team_min)

    # sort dicts
    tournaments_data['countries'] = sorted(tournaments_data['countries'].values(), key=itemgetter('count'), reverse=True)
    tournaments_data['clubs'] = sorted(tournaments_data['clubs'].values(), key=itemgetter('count'), reverse=True)
    tournaments_data['organizers'] = sorted(tournaments_data['organizers'].values(), key=itemgetter('count'), reverse=True)

    tournaments_data['ua_places'] = {k: v for k, v in
                                          sorted(tournaments_data['ua_places'].items(), key=lambda x: x[1],
                                                 reverse=True)}
    tournaments_data['foreign_places'] = {k: v for k, v in
                                          sorted(tournaments_data['foreign_places'].items(), key=lambda x: x[1],
                                                 reverse=True)}
    tournaments_data['ua_disciplines'] = {k: v for k, v in sorted(tournaments_data['ua_disciplines'].items(), key=lambda x: x[1], reverse=True)}
    tournaments_data['foreign_disciplines'] = {k: v for k, v in sorted(tournaments_data['foreign_disciplines'].items(), key=lambda x: x[1], reverse=True)}

    # calculate averages
    tournaments_data['ua_avg_teams_count'] = int(sum(tournaments_data['ua_teams_count']) / len(tournaments_data['ua_teams_count']))

    if len(tournaments_data['foreign_teams_count']) > 0:
        tournaments_data['foreign_avg_teams_count'] = int(sum(tournaments_data['foreign_teams_count']) / len(tournaments_data['foreign_teams_count']))
    else:
        tournaments_data['foreign_avg_teams_count'] = 0

    tournaments_data['ua_avg_players_count'] = int(sum(tournaments_data['ua_players_count']) / len(tournaments_data['ua_players_count']))

    if len(tournaments_data['foreign_players_count']) > 0:
        tournaments_data['foreign_avg_players_count'] = int(sum(tournaments_data['foreign_players_count']) / len(tournaments_data['foreign_players_count']))
    else:
        tournaments_data['foreign_avg_players_count'] = 0

    players_all = player_model.get_actual_players_list()
    if year is not None:
        players_all = season_model.objects.filter(year=year)

    return render(request, 'statistics/statistics.html', {
        'periods': periods,
        'active_period': str(year),
        'page_title': "Статистика порталу",
        'tournaments_all': tournaments_all,
        'tournaments_data': tournaments_data,
        'players_all': players_all,
    })