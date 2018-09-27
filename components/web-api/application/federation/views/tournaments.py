from django.shortcuts import render
from federation.models.tournament import Tournament, ArbiterTournamentMembership, TeamTournamentMembership
from django.shortcuts import get_object_or_404
import csv
from transliterate import translit
from django.http import HttpResponse


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
    tournament = get_object_or_404(Tournament, pk=id)
    arbiters = ArbiterTournamentMembership.objects.filter(tournament=tournament)
    teams = TeamTournamentMembership.objects.filter(tournament=tournament)

    return render(request, 'tournaments/tournament.html', {
        'tournament': tournament,
        'arbiters': arbiters,
        'teams': teams,
        'page_title': "Турнір",
    })


def tournament_teams_export(request, id):

    try:
        output_format = request.GET.get('format', 'html')
    except Exception:
        output_format = 'html'

    tournament = get_object_or_404(Tournament, pk=id)
    teams = TeamTournamentMembership.objects.filter(tournament=tournament)

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

    else:
        return render(request, 'tournaments/pure_teams_list.html', {
            'tournament': tournament,
            'teams': teams,
        })


def tournaments_calendar (request):
    return render(request, 'tournaments/calendar.html')


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
