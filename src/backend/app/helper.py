import csv
import io

from django.db.models import Count


from poll.models import Poll, ProjectAnswer, RoleAnswer
from poll.helper import get_project_ids_with_score_ordered
from team.models import Team

from .models import Project, Settings, Student, Role


# Opal export:
# 1. SE I -> Gruppenmanagement
# 2. Gruppe "Teilnehmer Projektarbeit"
# 3. Symbol Einträge auswählen: Vorname, Nachname, E-Mail-Adresse, Studiengruppe
# 4. Symbol Tabelle herunterladen -> table.xls
# 5. LibreOffice/Excell: als CSV-Datei speichern (Komma-Separator)
# 6. (Separator auf ',' ändern) (:%s/;/,/g)
def load_students_from_file(file, mode):
    if mode == "new":
        Student.objects.all().delete()

    data_set = file.read().decode("UTF-8")
    io_string = io.StringIO(data_set)
    next(io_string)
    for col in csv.reader(io_string, delimiter=",", quotechar="|"):
        # TODO: check/regex
        # - s_number s + 5 digits (perhaps longer for guest students)
        s_number = col[2][0:6]
        first_name = col[0]
        last_name = col[1]
        study_program = col[3][3:6]

        if Student.objects.filter(s_number=s_number).exists():
            continue

        values = {
            "first_name": first_name,
            "last_name": last_name,
            "study_program": study_program,
        }
        Student.objects.update_or_create(
            s_number=s_number,
            defaults=values,
        )


def reset_data():
    # delete data
    Team.objects.all().delete()
    Project.objects.all().delete()
    Student.objects.all().delete()
    Role.objects.all().delete()
    Settings.objects.all().delete()

    # delete lost table entries
    Poll.objects.all().delete()
    ProjectAnswer.objects.all().delete()
    RoleAnswer.objects.all().delete()

    # add default roles
    roles = [
        Role(name="Projektleitung"),
        Role(name="Analyse"),
        Role(name="Entwurf"),
        Role(name="Implementierung"),
        Role(name="Test"),
    ]
    Role.objects.bulk_create(roles)


def get_prepared_stats_for_view():
    stats = {}

    project_count = Project.objects.count()
    student_count = Student.objects.count()
    student_counts = Student.objects.values("study_program").annotate(total=Count("id"))
    role_count = Role.objects.count()
    team_count = Team.objects.values_list("project").distinct().count()

    stats["count"] = {
        "project": project_count,
        "student": student_count,
        "study_programs": student_counts,
        "role": role_count,
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

    project_ids = get_project_ids_with_score_ordered()
    projects = []
    for project_id in project_ids:
        score = project_id["total_score"]
        score_avg = project_id["avg_score"]
        project = Project.objects.get(id=project_id["project"])
        color = "text-primary"
        if Team.objects.exists():
            if Team.objects.filter(project=project).exists():
                color = "text-success"
            else:
                color = "text-danger"
        projects.append(
            {
                "pid": project.pid,
                "name": project.name,
                "score": score,
                "score_avg": score_avg,
                "color": color,
            }
        )

    stats["projects"] = projects

    return stats