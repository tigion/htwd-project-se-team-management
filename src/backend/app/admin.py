from django.contrib import admin
from .models import Project, Student, Role, Settings, Info

# Register your models here.
admin.site.register(Project)
admin.site.register(Student)
admin.site.register(Role)
admin.site.register(Settings)
admin.site.register(Info)