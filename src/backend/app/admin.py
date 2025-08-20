from django.contrib import admin
from .models import Project, Student, Settings, Info

# Register your models here.
admin.site.register(Project)
admin.site.register(Student)
admin.site.register(Settings)
admin.site.register(Info)
