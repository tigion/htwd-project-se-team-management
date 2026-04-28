from django.contrib import admin

from .models import LevelAnswer, Poll, ProjectAnswer

# Register your models here.
admin.site.register(Poll)
admin.site.register(ProjectAnswer)
admin.site.register(LevelAnswer)
