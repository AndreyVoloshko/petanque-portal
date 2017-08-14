from django.shortcuts import render
from django_bootstrap_carousel.models import Carousel

def main_page(request):
    carousel = Carousel.objects.get(pk=1)
    return render(request, 'main_page.html', {
            'carousel': carousel,
        })