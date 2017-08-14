from django.http import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

@login_required(login_url='/login/')
def application_logout(request):
    logout(request)
    return HttpResponseRedirect('/')
