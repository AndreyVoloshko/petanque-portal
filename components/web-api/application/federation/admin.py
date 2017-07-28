from django.contrib import admin
from .models import City, Club, Player

# Register your models here.
admin.site.register(City)
admin.site.register(Player)
admin.site.register(Club)