from django.shortcuts import render, redirect
from django.http import JsonResponse
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from django.shortcuts import get_object_or_404
from django.contrib import messages
import csv
from transliterate import translit
from django.http import HttpResponse
from django.conf import settings
from django.utils.html import escape
from django.http import HttpResponseRedirect
import logging, json


def tournaments(request, date_filter=None, type_filter=None):
    order=None
    frontend_order="asc"
    if date_filter == 'past':
        order = '-start_date'
        frontend_order = "desc"

    return render(request, 'tournaments/tournaments.html', {
        'tournaments': Tournament.get_list(date_filter=date_filter, type_filter=type_filter, custom_order=order),
        'initial_order': frontend_order,
        'page_title': "Турніри",
    })


def tournament(request, id):
    current_user = request.user

    tournament = get_object_or_404(Tournament, pk=id)

    if request.method == "POST":
        if 'tournament_notes_content' in request.POST and current_user.is_authenticated():
            if tournament.is_user_has_admin_access_to_tournament(current_user):
                tournament.final_notes = escape(request.POST['tournament_notes_content'])
                tournament.save()
                messages.success(request, 'Нотатки збережено.')
                return HttpResponseRedirect(request.path_info)

        if 'delete_team_id' in request.POST and current_user.is_authenticated():
            team = TeamTournamentMembership.objects.get(pk=request.POST['delete_team_id'])
            if team and team.is_user_has_admin_access_to_team(current_user):
                team.delete()
                messages.success(request, 'Комаду видалено.')
                return HttpResponseRedirect(request.path_info)

        if 'teams' in request.POST and current_user.is_authenticated():
            if tournament.is_user_has_admin_access_to_tournament(current_user):

                teams = json.loads(request.POST['teams'])

                for team in teams:
                    name_pieces = team['name'].split('-')
                    db_team = TeamTournamentMembership.objects.get(pk=name_pieces[0])

                    if db_team:

                        if not team['value']:
                            team['value'] = 0

                        if name_pieces[1] == 'min':
                            db_team.place_min = team['value']
                        elif name_pieces[1] == 'max':
                            db_team.place_max = team['value']
                        db_team.save()

                messages.success(request, 'Місця команд оновлено.')
                return HttpResponseRedirect(request.path_info)

    arbiters = ArbiterTournamentMembership.objects.filter(tournament=tournament)
    teams = TeamTournamentMembership.objects.filter(tournament=tournament)

    return render(request, 'tournaments/tournament.html', {
        'tournament': tournament,
        'arbiters': arbiters,
        'teams': teams,
        'page_title': "Турнір",
        'current_user': current_user
    })


def tournament_teams_export(request, id):

    try:
        output_format = request.GET.get('format', 'html')
    except Exception:
        output_format = 'html'

    tournament = get_object_or_404(Tournament, pk=id)
    teams = TeamTournamentMembership.objects.filter(tournament=tournament).order_by('place_min')

    if output_format == 'csv':

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv;charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="'+str(tournament.pk)+'-teams.csv"'
        writer = csv.writer(response,
                            delimiter=';',
                            lineterminator='\n',
                            quoting=csv.QUOTE_MINIMAL,
                            dialect='excel'
                            )

        row = [tournament.number_of_players_in_team_min]
        writer.writerow(row)

        row = []

        for i in range(1, tournament.number_of_players_in_team_min + 1):
            row.append("LASTNAME" + str(i))
            row.append("FIRSTNAME" + str(i))
            row.append("GENDER" + str(i))
            row.append("CLUB" + str(i))

        row.append("NAME")
        row.append("SEED")
        row.append("STATUS")
        row.append("RANK")
        writer.writerow(_encode_row(row))

        for team in tournament.teams.all():
            row = []
            player_index = 0

            for player in team.players.all():
                if player_index >= tournament.number_of_players_in_team_min:
                    break

                player_index += 1

                club_name = ""
                if player.current_club is not None:
                    club_name = player.current_club.name

                if player is not None:
                    row.append(player.name)
                    row.append(player.surname)
                    row.append(player.gender)
                    row.append(club_name)
                else:
                    # empty player
                    row.append("")
                    row.append("")
                    row.append("")
                    row.append("")

            row.append(team.get_short_name())
            row.append("0") # seed
            row.append("") # status
            row.append("") # rank

            writer.writerow(_encode_row(row))

        return response

    elif output_format == 'json':
        result = {
            'tournament': {
                'id': tournament.pk,
                'name': tournament.name,
                'date': tournament.start_date
            },
            'teams': []
        }

        for team in teams:
            current_team = {
                'id': team.team.pk,
                'power': team.power,
                'name': team.team.name,
                'players': []
            }

            for player in team.team.players.all():
                club_name = ""
                if player.current_club is not None:
                    club_name = player.current_club.name

                current_team['players'].append({
                    'id': player.pk,
                    'name': player.name,
                    'surname': player.surname,
                    'club': club_name
                })


            result['teams'].append(current_team)

        return JsonResponse(result)
    else:
        return render(request, 'tournaments/pure_teams_list.html', {
            'tournament': tournament,
            'teams': teams,
        })


def tournaments_calendar (request):
    return render(request, 'tournaments/calendar.html')


def tournament_protocol(request, id):
    tournament = get_object_or_404(Tournament, pk=id)

    if not tournament.is_processing_closed():
        return redirect('tournament', id=tournament.pk)

    if tournament.country != settings.CURRENT_COUNTRY:
        return redirect('tournament', id=tournament.pk)

    arbiters = ArbiterTournamentMembership.objects.filter(tournament=tournament)
    teams = TeamTournamentMembership.objects.filter(tournament=tournament).order_by('place_min')

    players_count = 0
    for team in teams:
        players_count += team.team.players.count()

    return render(request, 'tournaments/tournament_protocol.html', {
        'tournament': tournament,
        'arbiters': arbiters,
        'teams_count': len(teams),
        'teams': teams[:4],
        'players_count': players_count
    })


def _encode_row(values):
    tmp = []
    replace_mapping = [
        ('і', 'и'), ('ї', 'йи'), ('ґ', 'г'), ('є', 'е'),
        ('І', 'И'), ('Ї', 'Йи'), ('Ґ', 'Г'), ('Є', 'Е')
    ]

    for item in values:
        item = str(item)
        for k, v in replace_mapping:
            item = item.replace(k, v)

        tmp.append(translit(item, 'ru', reversed=True).encode("utf-8").decode("utf-8"))
    return tmp
