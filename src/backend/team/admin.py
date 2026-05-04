from django.contrib import admin

from .models import ProjectInstance, Team, TeamMember

# Register your models here.
admin.site.register(ProjectInstance)
admin.site.register(Team)
admin.site.register(TeamMember)
