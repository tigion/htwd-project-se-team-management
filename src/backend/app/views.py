import logging
from datetime import datetime

from django.contrib import messages
from django.core.files import File
from django.db.models import ProtectedError
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.html import format_html

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import AuthenticationForm
# from django.contrib.auth.models import User

from poll.models import POLL_SCORES
from poll.helper import (
    save_poll_data_to_db,
    load_poll_data_for_form,
    generate_poll_data_for_students_without_poll,
)

from team.models import ProjectInstance, Team
from team.helper import generate_teams, get_teams_for_view

from .models import Project, Settings, Student, Info
from .forms import (
    ProjectForm,
    StudentForm,
    UploadStudentsForm,
    SettingsForm,
    SettingsResetForm,
)
from .helper import (
    read_students_from_file_to_db,
    reset_data_in_db,
    get_statistics_for_view,
)
from .pdf import generate_teams_pdf

# Creates the logger.
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


@login_required
def student_home(request):
    settings = Settings.load()
    projects = Project.objects.all()

    student = Student.objects.filter(s_number=request.user.username).first()
    is_student = bool(student)

    context = {}
    context["is_student"] = is_student
    context["settings"] = settings
    context["projects"] = projects
    context["poll_scores"] = POLL_SCORES
    context["teams"] = get_teams_for_view().get("teams", [])

    if request.method == "POST" and is_student:
        # Check: Do only allow saving, if polls are writable
        if settings.poll_is_writable:
            # save poll data
            save_poll_data_to_db(student, request.POST, projects)
            return redirect("home")

    # load poll data to context for prefilled form
    form_poll_data = load_poll_data_for_form(student, projects)
    context["form_poll_data"] = form_poll_data

    return render(request, "student/home.html", context)


@login_required
@permission_required("app.view_project")
def projects(request):
    settings = Settings.load()

    context = {}
    context["settings"] = settings
    context["projects"] = Project.objects.all()

    return render(request, "lecturer/projects.html", context)


@login_required
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


@login_required
@permission_required("app.view_project")
@permission_required("app.delete_project")
# @permission_required("team.delete_projectinstance")
def project_delete(request, id=None):
    # TODO: ?
    # - https://www.pythontutorial.net/django-tutorial/django-delete-form/

    if request.method == "POST":
        project = get_object_or_404(Project, id=id)
        try:
            project.delete()
        except ProtectedError:
            messages.error(
                request,
                f'Achtung: Projekt "{project.pid_name}" kann nicht gelöscht werden, da es einem Team zugeteilt ist!',
            )

    return redirect("projects")


@login_required
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
                read_students_from_file_to_db(request.FILES.get("file"), request.POST.get("mode", 1))
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


@login_required
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


@login_required
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
                f'Achtung: Student "{student.name2}" kann nicht gelöscht werden, da er einem Team zugeteilt ist!',
            )

    return redirect("students")


@login_required
@permission_required("team.view_team")
def teams(request):
    settings = Settings.load()
    info = Info.load()

    context = {}
    context["is_management_view"] = True
    context["settings"] = settings
    context["info"] = info
    data = get_teams_for_view()
    context["teams"] = data.get("teams", [])
    context["total_happiness"] = data.get("happiness", {})

    return render(request, "lecturer/teams.html", context)


@login_required
@permission_required("team.add_team")
@permission_required("team.update_team")
@permission_required("team.delete_team")
def teams_generate(request):
    settings = Settings.load()

    if request.method == "POST":
        # Check: Do not allow generation, if teams are visible
        if not settings.teams_is_visible:
            # Check: Needed data
            if not Project.objects.exists() or not Student.objects.exists():
                messages.error(
                    request,
                    format_html(
                        'Achtung: Teamgenerierung fehlgeschlagen!<br /><ul class="mb-0"><li>Es müssen mindestens ein Projekte ({}) und ein Student ({}) vorhanden sein.</li></ul>',
                        Project.objects.count(),
                        Student.objects.count(),
                    ),
                )
                return redirect("teams")

        generate_poll_data_for_students_without_poll()
        generate_teams()

    return redirect("teams")


@login_required
@permission_required("team.delete_team")
def teams_delete(request):
    if request.method == "POST":
        Team.objects.all().delete()
        ProjectInstance.objects.all().delete()

    return redirect("teams")


@login_required
@permission_required("team.view_team")
def teams_print(request):
    if request.method == "POST":
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"teams_{timestamp}.pdf"
        response = FileResponse(generate_teams_pdf(), as_attachment=True, filename=filename)

        return response

    return redirect("teams")


@login_required
@permission_required("app.view_stats")
def stats(request):
    settings = Settings.load()

    context = {}
    context["settings"] = settings
    context["stats"] = get_statistics_for_view()

    return render(request, "lecturer/stats.html", context)


@login_required
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


@login_required
@permission_required("app.delete_project")
@permission_required("app.delete_student")
@permission_required("app.delete_settings")
@permission_required("team.delete_team")
@permission_required("poll.delete_poll")
@permission_required("poll.delete_projectanswer")
def settings_reset(request):
    if request.method == "POST":
        reset_data_in_db(request.POST.get("delete_only_polls_and_teams"))
        messages.success(request, "Die Daten wurden zurückgesetzt!")
        return redirect("home")

    return redirect("settings")


@login_required
@permission_required("app.view_settings")
def settings_backup(request):
    if request.method != "POST":
        return redirect("settings")

    from django.conf import settings

    # Checks if the database is SQLite.
    db_engine = settings.DATABASES["default"]["ENGINE"]
    if db_engine != "django.db.backends.sqlite3":
        messages.error(request, "Download des Datenbank-Backups ist aktuell nur für SQLite möglich!")
        return redirect("settings")

    # Sets the backup file name.
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"db_backup_{timestamp}.sqlite3"

    # Opens the database file.
    db_file = File(open(settings.DATABASES["default"]["NAME"], "rb"))

    # Variant 1: FileResponse
    # - content type (application/vnd.sqlite3) and length are set automatically
    response = FileResponse(db_file, as_attachment=True, filename=filename)

    # Variant 2: HttpResponse
    # response = HttpResponse(db_file, content_type="application/x-sqlite3")
    # response["Content-Disposition"] = f"attachment; filename={filename}"
    # response["Content-Length"] = db_file.size

    return response
