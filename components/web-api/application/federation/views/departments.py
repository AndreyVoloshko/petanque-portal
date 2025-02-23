from django.shortcuts import render
from django.shortcuts import get_object_or_404
from federation.models.department import Department


def departments(request):
    return render(request, 'departments/departments.html', {
        'departments': Department.objects.all().order_by('order'),
        'page_title': "Федерація петанку України"
    })