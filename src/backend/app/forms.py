from django import forms
from django.forms import ModelForm
from .models import (
    Project,
    Student,
    Settings,
)
from .helper import get_free_project_pids


class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ["pid", "name", "description", "technologies", "company", "contact", "url", "instances"]
        # fields = "__all__"

    def get_pid_choices(self, project):
        free_pids = get_free_project_pids()
        # Adds the current project to the list of free IDs.
        # Needed, if an existing project is edited.
        if project is not None:
            free_pids.append(project.pid)
            free_pids.sort()
        # Creates a list of tuples. 'A' -> ('A', 'A')
        pid_choices = list((pid, pid) for pid in free_pids)
        return pid_choices

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        self.fields["pid"] = forms.ChoiceField(
            label="Projekt-ID",
            choices=self.get_pid_choices(kwargs.get("instance")),
            help_text="Aktuell limitiert auf Grossbuchstaben von A bis Z",
        )


class StudentForm(ModelForm):
    class Meta:
        model = Student
        fields = "__all__"


class UploadStudentsForm(forms.Form):
    MODE_CHOICES = [
        ("add", "Anfügen von neuen Studenten"),
        ("new", "Ersetzen der vorhandenen Studenten"),
    ]
    file = forms.FileField(
        widget=forms.FileInput(attrs={"accept": ".csv"}),
        help_text="Studentenliste (aus Opal exportiert xls -> csv) als Komma separierte CSV-Datei mit Vorname, Nachname, E-Mail, Studiengruppe<br>bspw.: <code>Max,Mustermann,s00000@htw-dresden.de,21-041-01</code>",
    )
    mode = forms.ChoiceField(
        choices=MODE_CHOICES,
        initial="add",
        widget=forms.RadioSelect(),
    )


class SettingsForm(ModelForm):
    class Meta:
        model = Settings
        fields = "__all__"


class SettingsResetForm(forms.Form):
    delete_only_polls_and_teams = forms.BooleanField(
        required=False,
        initial=False,
        label="Nur Fragebogenantworten und Teams zurücksetzen",
        help_text="Wenn aktiv, werden nur die Fragebogenantworten und Teams gelöscht. Die Projekte, Studenten und Einstellungen bleiben beim Zurücksetzen erhalten.",
    )
    confirmed = forms.BooleanField(required=True, initial=False, label="Ich bin mir sicher")
