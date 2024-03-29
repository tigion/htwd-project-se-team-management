from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


# choices

TYPE_CHOICES = [
    ("i", "Intern"),
    ("e", "Extern"),
]

# TITLE_CHOICES = [
#     ("f", "Frau"),
#     ("h", "Herr"),
#     ("d", "Divers"),
# ]

STUDY_PROGRAM_CHOICES = [
    # Informatik/Mathematik
    ("041", "Informatik (041)"),
    ("042", "Wirtschaftsinformatik (042)"),
    ("048", "Verwaltungsinformatik (048)"),
    # Wirtschaftswissenschaften
    ("072", "Wirtschaftsingenieurwesen (072)"),
]


# models


class Project(models.Model):
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default=TYPE_CHOICES[0], verbose_name="Art")
    number = models.IntegerField(
        verbose_name="Nummer",
        help_text="Art und Nummer ergeben eine eindeutige Projekt-ID (bspw. I4, E2)",
    )
    # pid2 = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=255, verbose_name="Name")
    description = models.TextField(blank=True, null=True, verbose_name="Beschreibung")
    technologies = models.CharField(max_length=255, blank=True, null=True, verbose_name="Technologien")
    company = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Auftraggeber",
        help_text="Name der Firma, des Verein oder der Hochschule mit Fakultät",
    )
    contact = models.CharField(max_length=255, blank=True, null=True, verbose_name="Kontakt")
    url = models.URLField(
        blank=True,
        null=True,
        verbose_name="Link zu weiteren Informationen",
        help_text="PDF-Link zu den Projektbescheibungen in Opal",
    )

    class Meta:
        unique_together = ["type", "number"]
        ordering = (
            "type",
            "number",
        )

    @property
    def pid(self):
        return f"{self.type.upper()}{self.number}"

    @property
    def pid_name(self):
        return f"{self.pid}: {self.name}"

    def __str__(self):
        return f"{self.pid_name}"


class Student(models.Model):
    s_number = models.CharField(max_length=8, unique=True, verbose_name="Matrikelnummer")
    # title = models.CharField(max_length=1, choices=TITLE_CHOICES)
    first_name = models.CharField(max_length=255, verbose_name="Vorname")
    last_name = models.CharField(max_length=255, verbose_name="Nachname")
    study_program = models.CharField(max_length=3, choices=STUDY_PROGRAM_CHOICES, verbose_name="Studiengang")
    is_active = models.BooleanField(
        default=True,
        verbose_name="Nimmt am Projekt teil",
        help_text="Für Studenten die nicht mehr am Projekt teilnehmen, ist diese Option zu deaktivieren.",
    )

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def name2(self):
        return f"{self.name} ({self.s_number})"

    @property
    def email(self):
        return f"{self.s_number}@htw-dresden.de"

    @property
    def is_wing(self):
        return True if self.study_program == "072" else False

    @property
    def is_out(self):
        return not self.is_active

    def __str__(self) -> str:
        return f"{self.name2}"


class Role(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Name")

    def __str__(self) -> str:
        return f"{self.name}"


# settings
# - https://www.rootstrap.com/blog/simple-dynamic-settings-for-django


class Singleton(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super(Singleton, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Settings(Singleton):
    projects_is_visible = models.BooleanField(
        default=False,
        verbose_name="Projekte anzeigen",
        help_text="Wenn aktiv, sind die Projekte für die Studenten sichtbar.",
    )
    poll_is_visible = models.BooleanField(
        default=False,
        verbose_name="Fragebogen anzeigen",
        help_text="Wenn aktiv, ist der Fragebogen für die Studenten sichtbar.",
    )
    poll_is_writable = models.BooleanField(
        default=False,
        verbose_name="Fragebogen is ausfüllbar (schreibbar)",
        help_text="Wenn aktiv, kann der Fragebogen von den Studenten beantwortet bzw. geändert und abgesendet werden.",
    )
    teams_is_visible = models.BooleanField(
        default=False,
        verbose_name="Teams anzeigen",
        help_text="Wenn aktiv, sind die Teams für die Studenten sichtbar. Solange die Teams sichtbar sind, können keine Teams generiert oder verändert werden!",
    )
    team_min_member = models.IntegerField(
        default=6,
        verbose_name="Mindestanzahl der Studenten je Team",
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    wings_are_out = models.BooleanField(
        default=False,
        verbose_name="Wings für SE II in den Teams ausblenden",
        help_text="Wenn aktiv, werden die Wirtschaftsingenieure (Wings) für Software Engineering II in den Teams nicht mehr angezeigt. Sie nehmen nur an SE I teil.",
    )


class Info(Singleton):
    teams_last_update = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Zeitpunkt der letzten Teamänderung",
    )
    polls_last_update = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Zeitpunkt der letzten Umfrageänderung",
    )