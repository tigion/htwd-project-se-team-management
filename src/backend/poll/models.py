from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from app.models import Student, Project


POLL_SCORES = {
    "default": 3,
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

    # TODO: use POLL_SCORES for default, choices, validation
    score = models.PositiveIntegerField(
        default=POLL_SCORES["default"],
        # choices=SCORE_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    class Meta:
        unique_together = ["poll", "project"]

    def __str__(self) -> str:
        return f"{self.poll.student.name2} - {self.project.pid}"
