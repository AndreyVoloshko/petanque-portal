from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from federation.models.department import Department


def departments(request):
    return render(request, 'departments/departments.html', {
        'departments': Department.objects.all().order_by('order'),
        'page_title': _("Ukrainian Petanque Federation")
    })
