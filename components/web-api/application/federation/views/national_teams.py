from django.shortcuts import render
from federation.views.title_registry import national_team_groups, title_registry_context


def national_teams(request, team_id=None):
    return render(request, 'national_teams/national_teams.html', {
        **title_registry_context(
            'national_teams',
            national_team_groups(),
            active_group_key=f'team-{team_id}' if team_id is not None else None,
        ),
    })
