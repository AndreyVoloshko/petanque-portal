from django.shortcuts import render
from django.http import *
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

def application_login(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/profile/')

    if request.POST:
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is None:
            #
            # try to login using email
            #
            user_object = User.objects.get(email__iexact=username)
            if user_object is not None:
                user = authenticate(request, username=user_object.username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)

                next_url = '/profile/'
                if request.POST.get('next', ''):
                    next_url = request.POST.get('next', '')

                return HttpResponseRedirect(next_url)

    next = request.GET.get('next', '')

    return render(request, 'login.html', {
        'next': next
    })