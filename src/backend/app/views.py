from datetime import datetime

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.db.models import ProtectedError
from django.utils.html import format_html
from django.http import FileResponse

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, permission_required

from poll.models import POLL_SCORES
from poll.helper import (
    save_poll_data_to_db,
    load_poll_data_for_form,
    generate_poll_data_for_students_without_poll,
)

from team.models import Team
from team.helper import generate_teams, get_prepared_teams_for_view

from .models import Project, Settings, Student, Role, Info
from .forms import (
    ProjectForm,
    StudentForm,
    RoleForm,
    UploadStudentsForm,
    SettingsForm,
    SettingsResetForm,
)
from .helper import (
    load_students_from_file,
    reset_data,
    get_prepared_stats_for_view,
)
from .pdf import generate_teams_pdf

import logging

logger = logging.getLogger(__name__)

# Create your views here.


def signin(request):
    context = {}

    if request.user.is_authenticated:
        return redirect("home")

    form = AuthenticationForm(data=request.POST or None)

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = None

        # allow only login from lecturers students (table students)
        lecturers = ["dozent"]
        if username in lecturers or Student.objects.filter(s_number=username).exists():
            user = authenticate(request, username=username, password=password)

        if user is not None:
            # if user.is_active:
            login(request, user)
            messages.success(request, "Erfolgreich angemeldet")
            return redirect("home")
        else:
            logger.warning(f"Login error user: {username}")
            messages.error(request, "Anmeldung fehlgeschlagen")

    context["AuthenticationForm"] = form
    return render(request, "registration/login.html", context)


def signout(request):
    logout(request)
    return redirect("home")


@login_required(redirect_field_name=None, login_url="login")
def student_home(request):
    settings = Settings.load()
    projects = Project.objects.all()
    roles = Role.objects.all()

    student = Student.objects.filter(s_number=request.user.username).first()
    is_student = bool(student)

    context = {}
    context["is_student"] = is_student
    context["settings"] = settings
    context["projects"] = projects
    context["roles"] = roles
    context["poll_scores"] = POLL_SCORES
    context["teams"] = get_prepared_teams_for_view()

    if request.method == "POST" and is_student:
        # Check: Do only allow saving, if polls are writable
        if settings.poll_is_writable:
            # save poll data
            save_poll_data_to_db(student, request.POST, projects, roles)
            return redirect("home")

    # load poll data to context for prefilled form
    form_poll_data = load_poll_data_for_form(student, projects, roles)
    context["form_poll_data"] = form_poll_data

    return render(request, "student/home.html", context)


# @login_required(redirect_field_name=None, login_url="login")
@login_required
@permission_required("app.view_project")
def projects(request):
    settings = Settings.load()

    context = {}
    context["settings"] = settings
    context["projects"] = Project.objects.all()  # .order_by("type", "number")

    return render(request, "lecturer/projects.html", context)


@login_required()
@permission_required("app.view_project")
@permission_required("app.add_project")
@permission_required("app.change_project")
def project_edit(request, id=None):
    settings = Settings.load()

    context = {}
    context["settings"] = settings

    if id is None:
        form = ProjectForm(request.POST or None)
    else:
        project = get_object_or_404(Project, id=id)
        # project = Project.objects.get(id=id)
        form = ProjectForm(request.POST or None, instance=project)
        context["project"] = Project.objects.get(id=id)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("projects")

    context["ProjectForm"] = form
    return render(request, "lecturer/project.html", context)


@login_required()
@permission_required("app.view_project")
@permission_required("app.delete_project")
def project_delete(request, id=None):
    # context = {}

    # TODO:
    # https://www.pythontutorial.net/django-tutorial/django-delete-form/
    if request.method == "POST":
        project = get_object_or_404(Project, id=id)
        try:
            project.delete()
        except ProtectedError:
            messages.error(
                request,
                f'Achtung: Projekt "{ project.pid_name }" kann nicht gelöscht werden, da es einem Team zugeteilt ist!',
            )

    return redirect("projects")
    # context["projects"] = Project.objects.all().order_by("type", "number")
    # form = ProjectForm(request.POST or None)
    # context["ProjectForm"] = form
    # return render(request, "lecturer/projects.html", context)


@login_required()
@permission_required("app.view_student")
@permission_required("app.add_student")
@permission_required("app.change_student")
@permission_required("app.delete_student")
def students(request):
    settings = Settings.load()

    context = {}
    context["settings"] = settings
    context["students"] = Student.objects.all().order_by("last_name", "first_name", "s_number")

    form = UploadStudentsForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        # file = request.FILES["file"]
        # if not file.name.endswith("csv"):
        #     messages.info(request, "Please Upload the CSV File only")
        #     return ...
        if form.is_valid():
            try:
                load_students_from_file(request.FILES.get("file"), request.POST.get("mode", 1))
            except ProtectedError:
                messages.error(
                    request,
                    format_html(
                        'Achtung: Import von Studenten fehlgeschlagen!<br /><ul class="mb-0"><li>Studenten können nicht ersetzend importiert werden, solange vorhandene Studenten Teams zugeteilt sind</li></ul>',
                    ),
                )
            return redirect("students")

    context["UploadStudentsForm"] = form
    return render(request, "lecturer/students.html", context)


@login_required()
@permission_required("app.view_student")
@permission_required("app.add_student")
@permission_required("app.change_student")
def student_edit(request, id=None):
    settings = Settings.load()

    context = {}
    context["settings"] = settings

    if id is None:
        form = StudentForm(request.POST or None)
    else:
        student = get_object_or_404(Student, id=id)
        # student = Student.objects.get(id=id)
        form = StudentForm(request.POST or None, instance=student)
        context["student"] = Student.objects.get(id=id)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("students")

    context["StudentForm"] = form
    return render(request, "lecturer/student.html", context)


@login_required()
@permission_required("app.view_student")
@permission_required("app.delete_student")
def student_delete(request, id=None):
    if request.method == "POST":
        student = get_object_or_404(Student, id=id)
        try:
            student.delete()
        except ProtectedError:
            messages.error(
                request,
                f'Achtung: Student "{ student.name2 }" kann nicht gelöscht werden, da er einem Team zugeteilt ist!',
            )

    return redirect("students")


@login_required()
@permission_required("app.view_role")
def roles(request):
    settings = Settings.load()

    context = {}
    context["settings"] = settings
    context["roles"] = Role.objects.all()

    return render(request, "lecturer/roles.html", context)


@login_required()
@permission_required("app.view_role")
@permission_required("app.add_role")
@permission_required("app.change_role")
def role_edit(request, id=None):
    settings = Settings.load()

    context = {}
    context["settings"] = settings

    if id is None:
        form = RoleForm(request.POST or None)
    else:
        role = get_object_or_404(Role, id=id)
        # roll = Role.objects.get(id=id)
        form = RoleForm(request.POST or None, instance=role)
        context["role"] = Role.objects.get(id=id)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("roles")

    context["RoleForm"] = form
    return render(request, "lecturer/role.html", context)


@login_required()
@permission_required("app.view_role")
@permission_required("app.delete_role")
def role_delete(request, id=None):
    if request.method == "POST":
        role = get_object_or_404(Role, id=id)
        try:
            role.delete()
            messages.success(
                request,
                f'Rolle "{ role.name }" wurde gelöscht!',
            )
        except ProtectedError:
            messages.error(
                request,
                f'Achtung: Rolle "{ role.name }" kann nicht gelöscht werden, da sie für Teams verwendet wird!',
            )

    return redirect("roles")


@login_required()
@permission_required("team.view_team")
def teams(request):
    settings = Settings.load()
    info = Info.load()

    context = {}
    context["is_management_view"] = True
    context["settings"] = settings
    context["info"] = info
    context["teams"] = get_prepared_teams_for_view()

    return render(request, "lecturer/teams.html", context)


@login_required()
@permission_required("team.add_team")
@permission_required("team.update_team")
@permission_required("team.delete_team")
def teams_generate(request):
    settings = Settings.load()

    if request.method == "POST":
        # Check: Do not allow generation, if teams are visible
        if not settings.teams_is_visible:
            # Check: Needed data
            if not Project.objects.exists() or not Student.objects.exists() or Role.objects.count() < 2:
                messages.error(
                    request,
                    # f"Achtung: Für die Teamgenerierung müssen mindestens ein Projekte ({ Project.objects.count() }), ein Student ({ Student.objects.count() }) und midestens zwei Rollen ({ Role.objects.count() }) vorhanden sein!",
                    format_html(
                        'Achtung: Teamgenerierung fehlgeschlagen!<br /><ul class="mb-0"><li>es müssen mindestens ein Projekte ({}), ein Student ({}) und zwei Rollen ({}) vorhanden sein</li></ul>',
                        Project.objects.count(),
                        Student.objects.count(),
                        Role.objects.count(),
                    ),
                )
                return redirect("teams")

        generate_poll_data_for_students_without_poll()
        generate_teams()

    return redirect("teams")


@login_required()
@permission_required("team.delete_team")
def teams_delete(request):
    if request.method == "POST":
        Team.objects.all().delete()

    return redirect("teams")


@login_required()
@permission_required("team.view_team")
def teams_print(request):
    if request.method == "POST":
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"teams_{timestamp}.pdf"
        response = FileResponse(generate_teams_pdf(), as_attachment=True, filename=filename)

        return response

    return redirect("teams")


@login_required()
@permission_required("app.view_stats")
def stats(request):
    settings = Settings.load()

    context = {}
    context["settings"] = settings
    context["stats"] = get_prepared_stats_for_view()

    return render(request, "lecturer/stats.html", context)


@login_required()
@permission_required("app.view_settings")
@permission_required("app.add_settings")
@permission_required("app.change_settings")
@permission_required("app.delete_settings")
def settings(request):
    settings = Settings.load()

    context = {}
    context["settings"] = settings

    form = SettingsForm(request.POST or None, instance=settings)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("settings")

    context["SettingsForm"] = form
    context["SettingsResetForm"] = SettingsResetForm()
    return render(request, "lecturer/settings.html", context)


@login_required()
@permission_required("app.delete_project")
@permission_required("app.delete_student")
@permission_required("app.delete_role")
@permission_required("app.delete_settings")
@permission_required("team.delete_team")
@permission_required("poll.delete_poll")
@permission_required("poll.delete_projectanswer")
@permission_required("poll.delete_roleanswer")
def settings_reset(request):
    if request.method == "POST":
        reset_data()
        messages.success(request, "Die Daten wurden zurückgesetzt!")
        return redirect("home")

    return redirect("settings")