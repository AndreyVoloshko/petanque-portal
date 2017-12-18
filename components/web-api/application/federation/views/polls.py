# -*- coding: utf-8 -*-

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.http import Http404

from poll.utils import set_cookie
from poll.models import Poll, Item, Vote

@login_required(login_url='/login/')
def vote(request, poll_pk):
    if request.is_ajax():
        try:
            poll = Poll.objects.get(pk=poll_pk)
        except:
            raise Http404("Голосування не знайдено")

        item_pk = request.GET.get("item", False)
        if not item_pk:
            raise Http404("Відповідь не надіслано")

        try:
            item = Item.objects.get(pk=item_pk)
        except:
            raise Http404("Варіант не допустимий")

        if request.user.is_authenticated():
            user = request.user
        else:
            user = None

        user = request.user
        user_vote = Vote.objects.filter(poll=poll, user=user).count()
        if user_vote:
            raise Http404("Вже проголосовано")

        Vote.objects.create(
            poll=poll,
            ip=request.META['REMOTE_ADDR'],
            user=user,
            item=item,
        )

        response = HttpResponse(status=200)
        set_cookie(response, poll.get_cookie_name(), poll_pk)

        return response
    raise Http404("Голосувати напряму неможливо")

@login_required(login_url='/login/')
def poll(request, poll_pk):
    try:
        poll = Poll.objects.get(pk=poll_pk)
    except Exception:
        raise Http404("Голосування не знайдено")

    # redirect to results if already voted
    user = request.user
    user_vote = Vote.objects.filter(poll=poll, user=user).count()
    if user_vote > 0:
        return redirect('poll_result', poll_pk=poll_pk)

    # show poll
    items = Item.objects.filter(poll=poll)

    return render(request, "poll/poll.html", {
        'poll': poll,
        'items': items,
    })

@login_required(login_url='/login/')
def result(request, poll_pk):
    try:
        poll = Poll.objects.get(pk=poll_pk)
    except Exception:
        raise Http404("Голосування не знайдено")

    # redirect to poll if did not vote
    user = request.user
    user_vote = Vote.objects.filter(poll=poll, user=user).count()
    if user_vote <= 0:
        return redirect('poll', poll_pk=poll_pk)


    # show results
    items = Item.objects.filter(poll=poll)

    return render(request, "poll/result.html", {
        'poll': poll,
        'items': items,
})