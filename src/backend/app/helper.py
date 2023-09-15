import csv
import io

from .models import Project, Settings, Student, Role
from poll.models import Poll, ProjectAnswer, RoleAnswer
from team.models import Team


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