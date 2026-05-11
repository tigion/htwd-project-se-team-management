from app.models import Student
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from team.models import Team

FEEDBACK_SCORES = {
    "default": 3,
    "min": 1,
    "max": 5,
    "choices": {
        1: {
            "value": 1,
            "name": "very bad",
            "icon": "emoji-angry",
            "color": "red",
        },
        2: {
            "value": 2,
            "name": "bad",
            "icon": "emoji-frown",
            "color": "orange",
        },
        3: {
            "value": 3,
            "name": "neutral",
            "icon": "emoji-neutral",
            "color": "#FFD801",
        },
        4: {
            "value": 4,
            "name": "good",
            "icon": "emoji-smile",
            "color": "#9ACD32",
        },
        5: {
            "value": 5,
            "name": "very good",
            "icon": "emoji-heart-eyes",
            "color": "green",
        },
    },
}

# Create your models here.


# class Feedback(models.Model):
#     student = models.OneToOneField(Student, on_delete=models.CASCADE)
#
#     def __str__(self) -> str:
#         return f"{self.student.name2}"


class PeerFeedback1(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    team_member = models.ForeignKey(Student, on_delete=models.CASCADE)
    contribution_score = models.PositiveIntegerField(
        default=FEEDBACK_SCORES["default"],
        validators=[MinValueValidator(FEEDBACK_SCORES["min"]), MaxValueValidator(FEEDBACK_SCORES["max"])],
    )
    collaboration_score = models.PositiveIntegerField(
        default=FEEDBACK_SCORES["default"],
        validators=[MinValueValidator(FEEDBACK_SCORES["min"]), MaxValueValidator(FEEDBACK_SCORES["max"])],
    )
    reliability_score = models.PositiveIntegerField(
        default=FEEDBACK_SCORES["default"],
        validators=[MinValueValidator(FEEDBACK_SCORES["min"]), MaxValueValidator(FEEDBACK_SCORES["max"])],
    )
    reason = models.TextField(blank=True, null=True, verbose_name="Begründung")

    class Meta:
        # unique_together = ("team", "student", "team_member")
        constraints = (models.UniqueConstraint(fields=["team", "student", "team_member"], name="unique_peer_feedback"),)
        ordering = ("team__project_instance", "student", "team_member")

    def __str__(self) -> str:
        return f"{self.team} {self.student} - {self.team_member}"
