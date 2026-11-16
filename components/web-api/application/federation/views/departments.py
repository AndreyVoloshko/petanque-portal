from django.db.models import Exists, OuterRef, Prefetch
from django.shortcuts import render

from federation.models.department import Department, PlayerDepartmentMembership
from federation.views.title_registry import (
    ROUTE_CONFIG,
    title_registry_context,
)


def departments(request):
    return render(request, 'departments/departments.html', {
        **title_registry_context('departments', department_groups()),
    })


def public_departments():
    memberships = (
        PlayerDepartmentMembership.objects
        .filter(player__isnull=False)
        .select_related('player', 'player__current_club')
        .order_by('order', 'player__surname', 'player__name', 'pk')
    )

    return (
        Department.objects
        .filter(Exists(memberships.filter(team_id=OuterRef('pk'))))
        .prefetch_related(
            Prefetch(
                'playerdepartmentmembership_set',
                queryset=memberships,
                to_attr='ordered_memberships',
            )
        )
        .order_by('order', 'name', 'pk')
    )


def department_groups():
    groups = []
    for department in public_departments():
        label = department.name

        groups.append({
            'key': f'department-{department.pk}',
            'label': label,
            'short_label': department_badge(department),
            'items': [
                {
                    'player': membership.player,
                    'title_short': membership.role,
                    'title_label': membership.description or label,
                    'title_icon_class': ROUTE_CONFIG['departments']['icon_class'],
                }
                for membership in department.ordered_memberships
            ],
        })

    return groups


def department_badge(department):
    words = [
        word.strip('.,()[]{}').upper()
        for word in department.name.split()
        if word.strip('.,()[]{}')
    ]
    initials = ''.join(word[0] for word in words[:3] if word)

    return initials or 'ФПУ'
