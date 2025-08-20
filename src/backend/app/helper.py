import csv
import re

from io import StringIO

from django.db.models import Count

from poll.models import Poll, ProjectAnswer
from poll.helper import get_project_ids_with_score_ordered
from team.models import Team, ProjectInstance

from .models import STUDY_PROGRAM_CHOICES, Project, Settings, Student


# Opal export:
# 1. SE I -> Gruppenmanagement
# 2. Gruppe "Teilnehmer Projektarbeit"
# 3. Symbol Einträge auswählen: Vorname, Nachname, E-Mail-Adresse, Studiengruppe
# 4. Symbol Tabelle herunterladen -> table.xls
# 5. LibreOffice/Excell: als CSV-Datei speichern (Komma-Separator, Erste Zeile sind die Spaltennamen welche beim Import ignoriert werden)
# 6. (Falls notwending: Separator auf ',' ändern) (:%s/;/,/g)
def load_students_from_file(file, mode):
    if mode == "new":
        Student.objects.all().delete()

    # get study program ids
    study_program_ids = [sp[0] for sp in STUDY_PROGRAM_CHOICES]

    # read file data
    data_set = file.read().decode("UTF-8")
    io_string = StringIO(data_set)
    next(io_string)

    # parse data and ignore invalid students
    for col in csv.reader(io_string, delimiter=",", quotechar="|"):
        # s-number
        # - format: type + number
        #   - type: 's' (student) or 'gs' (guest student)
        #   - number: 1-9 digits
        # - source: 's00000@domain.com' -> 's00000'
        p = re.compile("^g?s[0-9]{1,9}@")
        if not p.match(col[2]):
            continue
        s_number = col[2].partition("@")[0].strip()  # part before mail domain

        # firstname
        first_name = col[0].strip()
        if not first_name:
            continue

        # lastname
        last_name = col[1].strip()
        if not last_name:
            continue

        # study program
        # - format: 3 digits '000'
        # - source: '21-041-01' -> '041'
        p = re.compile("^[0-9]{2}-[0-9]{3}-[0-9]{2}$")
        if not p.match(col[3]):
            continue
        study_program = col[3].split("-")[1].strip()  # middle part between '-'
        # limit to ids from STUDY_PROGRAM_CHOICES (app/models.py)
        if study_program not in study_program_ids:
            continue

        # ignore existing students
        if Student.objects.filter(s_number=s_number).exists():
            continue

        # save new student
        values = {
            "first_name": first_name,
            "last_name": last_name,
            "study_program": study_program,
        }
        Student.objects.update_or_create(
            s_number=s_number,
            defaults=values,
        )


def reset_data(delete_only_polls_and_teams=False):
    # delete only polls and teams
    if delete_only_polls_and_teams:
        Team.objects.all().delete()
        Poll.objects.all().delete()
        ProjectAnswer.objects.all().delete()
        return

    # delete all data
    Team.objects.all().delete()
    Project.objects.all().delete()
    Student.objects.all().delete()
    Settings.objects.all().delete()

    # delete lost table entries
    Poll.objects.all().delete()
    ProjectAnswer.objects.all().delete()


def get_prepared_stats_for_view():
    settings = Settings.load()
    stats = {}

    project_count = Project.objects.count()
    project_used_count = Project.objects.filter(projectinstance__team__isnull=False).distinct().count()
    project_instance_count = ProjectInstance.objects.count()
    student_count = Student.objects.count()
    student_out_count = Student.objects.filter(is_active=False).count()
    student_counts = Student.objects.values("study_program").annotate(total=Count("id"))
    team_count = Team.objects.values_list("project_instance").distinct().count()

    project_instance_used_count = int(student_count / settings.team_min_member)
    if project_used_count < 1:
        project_used_count = 1

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

    poll_count = Poll.objects.count()
    poll_empty_count = student_count - poll_count
    poll_filled_count = Poll.objects.filter(is_generated=False).count()
    poll_generated_count = Poll.objects.filter(is_generated=True).count()

    poll_percent = 0
    poll_empty_percent = 0
    poll_filled_percent = 0
    poll_generated_percent = 0
    if student_count > 0:
        poll_percent = 100 * poll_count / student_count
        poll_empty_percent = 100 - poll_percent
        poll_filled_percent = 100 * poll_filled_count / student_count
        poll_generated_percent = 100 * poll_generated_count / student_count

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

    # TODO: Order also by used projects?
    project_ids = get_project_ids_with_score_ordered()

    teams_exist = Team.objects.exists()
    projects = []
    for project_id in project_ids:
        score = project_id["total_score"]
        score_avg = project_id["avg_score"]
        project = Project.objects.get(id=project_id["project"])
        project_instances = ProjectInstance.objects.filter(project=project_id["project"])
        project_instances_used_count = (
            ProjectInstance.objects.filter(project=project_id["project"], team__isnull=False).distinct().count()
        )
        color = "text-primary"
        if teams_exist:
            project_is_used = Team.objects.filter(project_instance__in=project_instances).exists()
            if project_is_used:
                color = "text-success"
            else:
                color = "text-danger"
        projects.append({
            "pid": project.pid,
            "name": project.name,
            "instances": len(project_instances),
            "instances_used": project_instances_used_count,
            "score": score,
            "score_avg": score_avg,
            "color": color,
        })

    stats["projects"] = projects

    return stats


def get_object_counts():
    counts = {
        "project": Project.objects.count(),
        "student": Student.objects.count(),
        "team": Team.objects.values_list("project_instance").distinct().count(),
    }

    return counts
