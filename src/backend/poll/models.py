from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from app.models import Student, Project


POLL_SCORES = {
    "default": 3,
    "min": 1,
    "max": 5,
    "choices": [
        {
            "id": 1,
            "value": 1,
            "name": "very bad",
            "icon": "emoji-angry",
            "color": "red",
        },
        {
            "id": 2,
            "value": 2,
            "name": "bad",
            "icon": "emoji-frown",
            "color": "orange",
        },
        {
            "id": 3,
            "value": 3,
            "name": "neutral",
            "icon": "emoji-neutral",
            "color": "#FFD801",
        },
        {
            "id": 4,
            "value": 4,
            "name": "good",
            "icon": "emoji-smile",
            "color": "#9ACD32",
        },
        {
            "id": 5,
            "value": 5,
            "name": "very good",
            "icon": "emoji-heart-eyes",
            "color": "green",
        },
    ],
}

POLL_LEVELS = {
    "default": 1,
    "min": 1,
    "max": 4,
    "choices": {
        1: {
            "value": 1,
            "name": "keine Angabe",
            "icon": "record-fill",
            "color": "lightgrey",
        },
        2: {
            "value": 2,
            "name": "Besondere eigenständige Leistung erbringen",
            "icon": "caret-up-fill",
            "color": "green",
        },
        3: {
            "value": 3,
            "name": "Solides Verständnis von SE aufbauen",
            "icon": "record-fill",
            "color": "#9ACD32",
        },
        4: {
            "value": 4,
            "name": "Hauptsache bestehen",
            "icon": "caret-down-fill",
            "color": "red",
        },
    },
}


# Create your models here.


class Poll(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    is_generated = models.BooleanField(default=False)
    # timestamp = models.DateTimeField(auto_now_add=True)

    @property
    def is_wing(self):
        return self.student.is_wing

    def __str__(self) -> str:
        return f"{self.student.name2}"


class ProjectAnswer(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    # TODO: use POLL_SCORES choices, validation
    score = models.PositiveIntegerField(
        default=POLL_SCORES["default"],
        # choices=SCORE_CHOICES,
        validators=[MinValueValidator(POLL_SCORES["min"]), MaxValueValidator(POLL_SCORES["max"])],
    )

    class Meta:
        unique_together = ["poll", "project"]

    def __str__(self) -> str:
        return f"{self.poll.student.name2} - {self.project.pid}"


class LevelAnswer(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    level = models.PositiveIntegerField(
        default=POLL_LEVELS["default"],
        validators=[MinValueValidator(POLL_LEVELS["min"]), MaxValueValidator(POLL_LEVELS["max"])],
    )

    def __str__(self) -> str:
        return f"{self.poll.student.name2}"
