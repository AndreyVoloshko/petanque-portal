from django.shortcuts import render
from django.http import *
from django.contrib.auth import authenticate, login, logout

def application_login(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/profile/')

    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect('/profile/')

    return render(request, 'login.html', {})