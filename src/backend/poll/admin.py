from django.contrib import admin
from .models import Poll, ProjectAnswer, RoleAnswer

# Register your models here.
admin.site.register(Poll)
admin.site.register(ProjectAnswer)
admin.site.register(RoleAnswer)
