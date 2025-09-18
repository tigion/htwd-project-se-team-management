import csv
import re

from io import StringIO

from django.db.models import Count

from poll.models import POLL_SCORES, POLL_LEVELS, Poll, ProjectAnswer, LevelAnswer
from poll.helper import get_project_ids_ordered_by_score
from team.models import Team, ProjectInstance

from .models import STUDY_PROGRAM_CHOICES, Project, Settings, Student, Info


def get_free_project_pids() -> list:
    """
    Returns a list of free project PIDs (pid).

    The pid is not the pk (id) of a project object.
    """

    # TODO: The allowed PID letters A-Z are currently hard-coded
    #       and limits the number of projects to 26.

    allowed_pids = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    used_pids = list(Project.objects.values_list("pid", flat=True))
    free_pids = list(pid for pid in allowed_pids if pid not in used_pids)

    return free_pids


def read_students_from_file_to_db(file, mode):
    """
    Reads the students from the given file and saves them to the database.
    Ignores invalid and existing students.

    Modes:
    - "add": Adds only new students (default).
    - "new": Deletes all existing students and creates new ones.

    Args:
        file: The file to read.
        mode: The mode to use. Can be "add" or "new".
    """

    # NOTE: Export students from Opal:
    #
    # 1. SE I -> Gruppenmanagement
    # 2. Gruppe "Teilnehmende Projektarbeit" -> "Mitglieder verwalten" -> "Teilnehmer"
    # 3. Symbol Einträge auswählen: Vorname, Nachname, E-Mail-Adresse, Studiengruppe
    # 4. Alle Studenten auswählen
    # 5. Symbol Tabelle herunterladen -> table.xlsx
    # 6. LibreOffice/Excel: als CSV-Datei speichern (Komma-Separator, Erste Zeile sind die Spaltennamen welche beim Import ignoriert werden)
    # 7. (Falls notwending: Separator auf ',' ändern) (:%s/;/,/g)

    # Deletes all existing students if mode is "new".
    if mode == "new":
        Student.objects.all().delete()

    # Gets the study program IDs.
    study_program_ids = [sp[0] for sp in STUDY_PROGRAM_CHOICES]

    # Reads the data from the file.
    data_set = file.read().decode("UTF-8")
    io_string = StringIO(data_set)
    next(io_string)  # Skips the header line.

    # Creates the patterns to match a student ID and a study program.
    student_id_pattern = re.compile("^g?s[0-9]{1,9}@")
    study_program_pattern = re.compile("^[0-9]{2}-[0-9]{3}-[0-9]{2}$")

    # Parses the read data and creates new valid students.
    for col in csv.reader(io_string, delimiter=",", quotechar="|"):
        # Sets the s-number. Continues if the student ID is not valid.
        # - format: type + number
        #   - type: 's' (student) or 'gs' (guest student)
        #   - number: 1-9 digits
        # - source: 's00000@domain.com' -> 's00000'
        if not student_id_pattern.match(col[2]):
            continue
        # Uses the part before the mail domain for the s-number.
        s_number = col[2].partition("@")[0].strip()

        # Sets the first name. Continues if no first name.
        first_name = col[0].strip()
        if not first_name:
            continue

        # Sets the last name. Continues if no last name.
        last_name = col[1].strip()
        if not last_name:
            continue

        # Sets the study program. Continues if the study program is not valid.
        # - format: 3 digits '000'
        # - source: '21-041-01' -> '041'
        if not study_program_pattern.match(col[3]):
            continue
        # Uses the middle part between '-' for the study program.
        study_program = col[3].split("-")[1].strip()
        # limit to ids from STUDY_PROGRAM_CHOICES (app/models.py)
        if study_program not in study_program_ids:
            continue

        # Ignores existing students.
        if Student.objects.filter(s_number=s_number).exists():
            continue

        # Saves the new student.
        values = {
            "first_name": first_name,
            "last_name": last_name,
            "study_program": study_program,
        }
        Student.objects.update_or_create(s_number=s_number, defaults=values)


def reset_data_in_db(delete_only_polls_and_teams=False):
    """
    Deletes all data and sets the settings to their default values.

    Args:
        delete_only_polls_and_teams: If True, only the polls and teams are deleted.
    """

    # Deletes only the polls and teams.
    if delete_only_polls_and_teams:
        Team.objects.all().delete()
        ProjectInstance.objects.all().delete()
        Poll.objects.all().delete()
        ProjectAnswer.objects.all().delete()
        Info.objects.all().delete()
        return

    # Deletes all data
    Team.objects.all().delete()
    Project.objects.all().delete()
    Student.objects.all().delete()
    Settings.objects.all().delete()
    Info.objects.all().delete()

    # Deletes possible lost table entries.
    Poll.objects.all().delete()
    ProjectAnswer.objects.all().delete()


def get_counts_for_view() -> dict:
    """
    Returns the number of projects, students and teams.
    """

    counts = {
        "project": Project.objects.count(),
        "student": Student.objects.count(),
        "team": Team.objects.values_list("project_instance").distinct().count(),
    }

    return counts


def get_statistics_for_view() -> dict:
    """
    Returns the prepared statistics for the view.
    """

    settings = Settings.load()
    stats = {}

    # Gets the number of objects in the database.
    project_count = Project.objects.count()
    project_used_count = Project.objects.filter(projectinstance__team__isnull=False).distinct().count()
    project_instance_count = ProjectInstance.objects.count()
    student_count = Student.objects.count()
    student_out_count = Student.objects.filter(is_active=False).count()
    student_counts = Student.objects.values("study_program").annotate(total=Count("id"))
    team_count = Team.objects.values_list("project_instance").distinct().count()

    # Sets the number of project instances to use.
    project_instance_used_count = int(student_count / settings.team_min_member)

    # Fills the "count" part.
    stats["count"] = {
        "project": project_count,
        "project_used": project_used_count,
        "project_instance": project_instance_count,
        "project_instance_used": project_instance_used_count,
        "student": student_count,
        "student_out": student_out_count,
        "study_programs": student_counts,
        "team": team_count,
    }

    # Gets the number of polls and poll states.
    poll_count = Poll.objects.count()
    poll_empty_count = student_count - poll_count
    poll_filled_count = Poll.objects.filter(is_generated=False).count()
    poll_generated_count = Poll.objects.filter(is_generated=True).count()

    # Sets the percentages of polls and poll states.
    poll_percent = 0
    poll_empty_percent = 0
    poll_filled_percent = 0
    poll_generated_percent = 0
    if student_count > 0:
        poll_percent = 100 * poll_count / student_count
        poll_empty_percent = 100 - poll_percent
        poll_filled_percent = 100 * poll_filled_count / student_count
        poll_generated_percent = 100 * poll_generated_count / student_count

    # Fills the "poll" part.
    stats["poll"] = {
        "all": {
            "count": poll_count,
            "percent": poll_percent,
        },
        "filled": {
            "count": poll_filled_count,
            "percent": poll_filled_percent,
        },
        "generated": {
            "count": poll_generated_count,
            "percent": poll_generated_percent,
        },
        "empty": {
            "count": poll_empty_count,
            "percent": poll_empty_percent,
        },
    }

    # Fill the "level" part.
    level_counts = []
    for key, poll_level in POLL_LEVELS["choices"].items():
        level_count = LevelAnswer.objects.filter(level=poll_level["value"]).count()
        level_counts.append({
            "level": poll_level,
            "count": level_count,
        })
    stats["level"] = level_counts

    # Sets the project IDs ordered by the total score.
    project_ids = get_project_ids_ordered_by_score()

    # Sets the project information per project.
    teams_exist = Team.objects.exists()
    projects = []
    for project_id in project_ids:
        # Sets the score and average score.
        poll_score = project_id["total_score"]
        score_avg = project_id["avg_score"]

        # Sets the score counts.
        score_counts = []

        for _, x_poll_score in sorted(POLL_SCORES["choices"].items(), key=lambda x: x[1]["value"], reverse=True):
            score_counts.append({
                "score": x_poll_score,
                "count": ProjectAnswer.objects.filter(
                    project=project_id["project"], score=x_poll_score["value"]
                ).count(),
            })

        # Gets the project.
        project = Project.objects.get(id=project_id["project"])
        # Gets the project instances.
        project_instances = ProjectInstance.objects.filter(project=project_id["project"])
        project_instances_used_count = (
            ProjectInstance.objects.filter(project=project_id["project"], team__isnull=False).distinct().count()
        )
        # Sets the color of the project.
        color = "text-primary"
        if teams_exist:
            project_is_used = Team.objects.filter(project_instance__in=project_instances).exists()
            if project_is_used:
                color = "text-success"
            else:
                color = "text-danger"

        # Fills and adds the project information.
        projects.append({
            "pid": project.pid,
            "name": project.name,
            "instances": len(project_instances),
            "instances_used": project_instances_used_count,
            "score": poll_score,
            "score_avg": score_avg,
            "score_counts": score_counts,
            "color": color,
        })

    # Fills the "projects" part.
    stats["projects"] = projects

    return stats
