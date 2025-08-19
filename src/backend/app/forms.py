from django import forms
from django.forms import ModelForm
from .models import (
    Project,
    Student,
    # Role,
    Settings,
)


class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = "__all__"


class StudentForm(ModelForm):
    class Meta:
        model = Student
        fields = "__all__"


# class RoleForm(ModelForm):
#     class Meta:
#         model = Role
#         fields = "__all__"


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
    delete_only_polls = forms.BooleanField(
        required=False,
        initial=False,
        label="Nur Fragebogenantworten und Teams löschen",
        help_text="Wenn aktiv, werden nur die Fragebogenantworten und Teams gelöscht. Die Projekte, Studenten und Einstellungen bleiben beim Zurücksetzen erhalten.",
    )
    confirmed = forms.BooleanField(required=True, initial=False, label="Ich bin mir sicher")
