from app.models import Student
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import models
from team.models import Team

FEEDBACK_SCORES = {
    "default": 3,
    "min": 1,
    "max": 5,
    "choices": {
        1: {
            "value": 1,
            "name": "sehr schlecht",
            "icon": "emoji-angry",
            "color": "red",
        },
        2: {
            "value": 2,
            "name": "schlecht",
            "icon": "emoji-frown",
            "color": "orange",
        },
        3: {
            "value": 3,
            "name": "durchschnittlich",
            "icon": "emoji-neutral",
            "color": "#FFD801",
        },
        4: {
            "value": 4,
            "name": "gut",
            "icon": "emoji-smile",
            "color": "#9ACD32",
        },
        5: {
            "value": 5,
            "name": "sehr gut",
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
    reviewing_student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="given_peer_feedback")
    reviewed_student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="received_peer_feedback")
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
    reason = models.TextField(validators=[MinLengthValidator(20)], verbose_name="Begründung")

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["team", "reviewing_student", "reviewed_student"], name="unique_peer_feedback"
            ),
        )
        ordering = ("team__project_instance", "reviewing_student", "reviewed_student")

    def __str__(self) -> str:
        return f"{self.team} {self.reviewing_student} - {self.reviewed_student}"
