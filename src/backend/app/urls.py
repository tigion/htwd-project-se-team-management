from django.urls import path
from . import views

urlpatterns = [
    # Home
    path("", views.student_home, name="home"),
    # Login/Logout
    path("login/", views.signin, name="login"),
    path("logout/", views.signout, name="logout"),
    # Projects
    path("projects/", views.projects, name="projects"),
    path("projects/add", views.project_edit, name="project-add"),
    path("projects/<int:id>", views.project_edit, name="project-update"),
    path("projects/<int:id>/delete", views.project_delete, name="project-delete"),
    # Students
    path("students/", views.students, name="students"),
    path("students/add", views.student_edit, name="student-add"),
    path("students/<int:id>", views.student_edit, name="student-update"),
    path("students/<int:id>/delete", views.student_delete, name="student-delete"),
    # Teams
    path("teams/", views.teams, name="teams"),
    path("teams/generate", views.teams_generate, name="teams-generate"),
    path("teams/delete", views.teams_delete, name="teams-delete"),
    path("teams/print", views.teams_print, name="teams-print"),
    # Statistics
    path("stats/", views.stats, name="stats"),
    # Settings
    path("settings/", views.settings, name="settings"),
    path("settings/reset", views.settings_reset, name="reset"),
    path("settings/backup", views.settings_backup, name="backup"),
]
