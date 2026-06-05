from django.db.models import Prefetch
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


def department_groups():
    groups = []
    memberships = (
        PlayerDepartmentMembership.objects
        .filter(player__isnull=False)
        .select_related('player', 'player__current_club')
        .order_by('order', 'player__surname', 'player__name')
    )

    departments_list = (
        Department.objects
        .prefetch_related(
            Prefetch(
                'playerdepartmentmembership_set',
                queryset=memberships,
                to_attr='ordered_memberships',
            )
        )
        .order_by('order', 'name')
    )

    for department in departments_list:
        if not department.ordered_memberships:
            continue

        label = department.name
        group_short_label = _short_label_from_text(label, 'ФПУ')

        groups.append({
            'key': f'department-{department.pk}',
            'label': label,
            'short_label': group_short_label,
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


def _short_label_from_text(text, fallback):
    words = [
        word.strip('.,()[]{}').upper()
        for word in str(text).split()
        if word.strip('.,()[]{}')
    ]
    initials = ''.join(word[0] for word in words[:3] if word)

    return initials or fallback
