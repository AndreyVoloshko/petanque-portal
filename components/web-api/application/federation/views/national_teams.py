from django.shortcuts import render
from federation.models.national_teams import National_team, PlayerNational_teamMembership


def national_teams(request, team_id=None):
    teams = National_team.objects.all()

    current_team = teams[0]
    current_team_players = PlayerNational_teamMembership.objects.filter(team=current_team)
    if team_id is not None:
        current_team = National_team.objects.get(pk=team_id)
        current_team_players = PlayerNational_teamMembership.objects.filter(team=current_team)

    return render(request, 'national_teams/national_teams.html', {
        'teams': teams,
        'current_team': current_team,
        'current_team_players': current_team_players,
        'page_title': "Національні збірні України",
    })