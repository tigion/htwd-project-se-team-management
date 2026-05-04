import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import ProtectedError
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from poll.helper import (
    delete_poll_data_for_student,
    generate_missing_poll_data,
    generate_missing_poll_data_for_student,
    load_poll_data_for_form,
    save_poll_data_to_db,
)
from poll.models import POLL_LEVELS, POLL_SCORES
from team.algorithm import AssignmentAlgorithm
from team.forms import TeamForm
from team.helper import delete_team_member_data_for_student, generate_teams, get_teams_for_view
from team.models import ProjectInstance, Team, TeamMember

from .forms import (
    DevSettingsForm,
    ProjectForm,
    SettingsForm,
    SettingsResetForm,
    StudentForm,
    UploadStudentsForm,
)
from .helper import (
    get_statistics_for_view,
    get_students_for_view,
    read_students_from_file_to_db,
    reset_data_in_db,
)
from .models import DevSettings, Info, Project, Settings, Student
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
    context["poll_levels"] = POLL_LEVELS
    context["teams"] = get_teams_for_view().get("teams", [])

    if request.method == "POST" and is_student and settings.poll_is_writable:
        # save poll data
        save_poll_data_to_db(student, request.POST, projects)
        messages.success(
            request,
            "Antworten gespeichert. Änderungen sind möglich, solange der Fragebogen nicht gesperrt ist.",
        )
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

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("projects")

    context["ProjectForm"] = form
    return render(request, "lecturer/project.html", context)


@login_required
@permission_required("app.view_project")
@permission_required("app.delete_project")
# @permission_required("team.delete_projectinstance")
def project_delete(request, id=None):
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
    context["students"] = get_students_for_view()
    # context["project_instances"] = ProjectInstance.objects.all()
    context["teams"] = Team.objects.all()

    form = UploadStudentsForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            read_students_from_file_to_db(request.FILES.get("file"), request.POST.get("mode", 1))
        except ProtectedError:
            messages.error(
                request,
                mark_safe(
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

    if request.method == "POST" and form.is_valid():
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

        # Do not allow deletion of student, if he is assigned to a team with a project instance.
        if TeamMember.objects.filter(
            student=student, project_instance__isnull=False
        ).exists():  # TODO: Use Team objects.
            messages.error(
                request,
                f'Achtung: Student "{student.name2}" kann nicht gelöscht werden, da er einem Team zugeordnet ist!',
            )
            return redirect("students")

        try:
            delete_poll_data_for_student(student.pk)
            delete_team_member_data_for_student(student.pk)
            student.delete()
            messages.success(request, f'Student "{student.name2}" wurde gelöscht!')
        except ProtectedError:
            messages.error(
                request,
                f'Achtung: Student "{student.name2}" kann nicht gelöscht werden, es bestehen noch Abhängigkeiten in der Datenbank!',
            )

    return redirect("students")


@login_required
@permission_required("app.view_student")
def student_set_team(request, id=None):  # TODO: Use Team objects.
    if request.method == "POST":
        student = get_object_or_404(Student, id=id)
        team_id = request.POST.get("team_id")

        # Remove team assignment if project_instance_id is "0".
        if team_id == "0":
            team_member = TeamMember.objects.filter(student=student).first()
            if team_member:
                old_piid = team_member.team.project_instance.piid
                team_member.delete()
                messages.success(request, f'Student "{student.name2}" wurde aus Team {old_piid} entfernt!')
            return redirect("students")

        team = Team.objects.filter(pk=team_id).first() if team_id else None

        # Do not allow setting team, if no team is found for the given id.
        if not team:
            messages.error(
                request, "Achtung: Teamzuweisung fehlgeschlagen! Es muss eine gültiges Team ausgewählt werden."
            )
            return redirect("students")

        # Set new team assignment for the student. If no team exists yet, create a new one.
        team_member = TeamMember.objects.filter(student=student).first()
        if team_member and team_member.team != team:
            old_piid = team_member.team.project_instance.piid
            team_member.team = team
            team_member.save()
            msg = f'Student "{student.name2}" wurde von Team {old_piid} in Team {team_member.team.project_instance.piid} verschoben!'
            messages.success(request, msg)

        else:
            generate_missing_poll_data_for_student(student)
            team_member = TeamMember.objects.create(
                team=team,
                student=student,
                score=50,  # default score from algorithm (currently unused)
            )
            messages.success(
                request, f'Student "{student.name2}" wurde Team {team_member.team.project_instance.piid} zugewiesen!'
            )

    return redirect("students")


@login_required
@permission_required("team.view_team")
def teams(request):
    settings = Settings.load()
    dev_settings = DevSettings.load()
    info = Info.load()

    context = {}
    context["is_management_view"] = True
    context["settings"] = settings
    context["dev_settings"] = dev_settings
    context["is_team_generation_running"] = AssignmentAlgorithm.get_is_running()
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
        # Check: Do not allow generation, if teams are visible or if there are no projects or students.
        if not settings.teams_is_visible and (not Project.objects.exists() or not Student.objects.exists()):
            messages.error(
                request,
                format_html(
                    'Achtung: Teamgenerierung fehlgeschlagen!<br /><ul class="mb-0"><li>Es müssen mindestens ein Projekte ({}) und ein Student ({}) vorhanden sein.</li></ul>',
                    Project.objects.count(),
                    Student.objects.count(),
                ),
            )
            return redirect("teams")

        generate_missing_poll_data()
        generate_teams()

    return redirect("teams")


@login_required
@permission_required("team.delete_team")
def teams_delete(request):
    if request.method == "POST":
        TeamMember.objects.all().delete()
        ProjectInstance.objects.all().delete()

    return redirect("teams")


@login_required
@permission_required("team.view_team")
def teams_print(request):
    if request.method == "POST":
        timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d-%H%M%S")
        filename = f"teams_{timestamp}.pdf"
        response = FileResponse(generate_teams_pdf(), as_attachment=True, filename=filename)

        return response

    return redirect("teams")


@login_required
@permission_required("app.view_team")
@permission_required("app.add_team")
@permission_required("app.change_team")
def team_edit(request, id=None):
    settings = Settings.load()

    context = {}
    context["settings"] = settings

    if id is None:
        form = TeamForm(request.POST or None)
    else:
        team = get_object_or_404(Team, pk=id)
        form = TeamForm(request.POST or None, instance=team)
        context["team"] = Team.objects.get(pk=id)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("teams")

    context["TeamForm"] = form
    return render(request, "lecturer/team.html", context)


@login_required
@permission_required("app.view_stats")
def stats(request):
    settings = Settings.load()

    context = {}
    context["settings"] = settings
    context["poll_scores"] = POLL_SCORES
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

    if request.method == "POST" and form.is_valid():
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
    timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d-%H%M%S")
    filename = f"db_backup_{timestamp}.sqlite3"

    # Opens the database file.
    response = FileResponse(
        open(settings.DATABASES["default"]["NAME"], "rb"),  # noqa: SIM115 (Django FileResponse context)
        as_attachment=True,
        filename=filename,
    )

    # Variant 1: FileResponse
    # - content type (application/vnd.sqlite3) and length are set automatically
    # response = FileResponse(db_file, as_attachment=True, filename=filename)
    #
    # Variant 2: HttpResponse
    # response = HttpResponse(db_file, content_type="application/x-sqlite3")
    # response["Content-Disposition"] = f"attachment; filename={filename}"
    # response["Content-Length"] = db_file.size

    return response


@login_required
@permission_required("app.view_devsettings")
@permission_required("app.add_devsettings")
@permission_required("app.change_devsettings")
@permission_required("app.delete_devsettings")
def dev_settings(request):
    settings = Settings.load()
    dev_settings = DevSettings.load()

    context = {}
    context["settings"] = settings
    context["dev_settings"] = dev_settings

    form = DevSettingsForm(request.POST or None, instance=dev_settings)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("dev")

    context["DevSettingsForm"] = form
    return render(request, "lecturer/dev-settings.html", context)
