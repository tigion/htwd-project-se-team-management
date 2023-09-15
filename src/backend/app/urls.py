from django.urls import path
from . import views

urlpatterns = [
    # home
    path("", views.student_home, name="home"),
    # login
    path("login/", views.signin, name="login"),
    path("logout/", views.signout, name="logout"),
    # projects
    path("projects/", views.projects, name="projects"),
    path("projects/add", views.project_edit, name="project-add"),
    path("projects/<int:id>", views.project_edit, name="project-update"),
    path("projects/<int:id>/delete", views.project_delete, name="project-delete"),
    # students
    path("students/", views.students, name="students"),
    path("students/add", views.student_edit, name="student-add"),
    path("students/<int:id>", views.student_edit, name="student-update"),
    path("students/<int:id>/delete", views.student_delete, name="student-delete"),
    # roles
    path("roles/", views.roles, name="roles"),
    path("roles/add", views.role_edit, name="role-add"),
    path("roles/<int:id>", views.role_edit, name="role-update"),
    path("roles/<int:id>/delete", views.role_delete, name="role-delete"),
    # teams
    path("teams/", views.teams, name="teams"),
    path("teams/generate", views.teams_generate, name="teams-generate"),
    path("teams/delete", views.teams_delete, name="teams-delete"),
    # settings
    path("settings/", views.settings, name="settings"),
    path("settings/reset", views.settings_reset, name="reset"),
]
