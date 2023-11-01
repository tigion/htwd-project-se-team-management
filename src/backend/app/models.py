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
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default=TYPE_CHOICES[0])
    number = models.IntegerField(
        verbose_name="Nummer",
        help_text="Type und Nummer ergeben eine eindeutige ProjektID (bspw. I4, E2)",
    )
    # pid2 = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    technologies = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    contact = models.CharField(max_length=255, blank=True, null=True)
    url = models.URLField(blank=True, null=True)

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
    s_number = models.CharField(max_length=8, unique=True)
    # title = models.CharField(max_length=1, choices=TITLE_CHOICES)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    study_program = models.CharField(max_length=3, choices=STUDY_PROGRAM_CHOICES)

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

    def __str__(self) -> str:
        return f"{self.name2}"


class Role(models.Model):
    name = models.CharField(max_length=255, unique=True)

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
    projects_is_visible = models.BooleanField(default=False, verbose_name="Projekte anzeigen")
    poll_is_visible = models.BooleanField(default=False, verbose_name="Fragebogen anzeigen")
    poll_is_writable = models.BooleanField(
        default=False,
        verbose_name="Fragebogen is ausfüllbar (schreibbar)",
        help_text="Wenn aktiv, kann der Fragebogen beantwortet bzw. geändert und abgesendet werden."
    )
    teams_is_visible = models.BooleanField(
        default=False,
        verbose_name="Teams anzeigen",
        help_text="Wenn aktiv, können keine Teams mehr generiert oder verändert werden!",
    )
    team_min_member = models.IntegerField(
        default=6,
        verbose_name="Mindestanzahl der Studenten je Team",
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )


class Info(Singleton):
    teams_last_update = models.DateTimeField(blank=True, null=True)
    polls_last_update = models.DateTimeField(blank=True, null=True)