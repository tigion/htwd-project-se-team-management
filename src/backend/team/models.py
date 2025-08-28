from django.db import models
from app.models import Project, Student


# Create your models here.


class ProjectInstance(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    number = models.IntegerField()

    class Meta:
        # unique_together = ["project", "number"]  # may be deprecated in the future
        constraints = [
            models.UniqueConstraint(fields=["project", "number"], name="unique_project_number"),
        ]
        ordering = (
            "project",
            "number",
        )

    @property
    def piid(self):
        return f"{self.project.pid}{self.number}"

    def __str__(self) -> str:
        return f"{self.piid}"


class Team(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    project_instance = models.ForeignKey(ProjectInstance, on_delete=models.PROTECT, blank=True, null=True)
    student = models.OneToOneField(Student, on_delete=models.PROTECT, unique=True)
    student_is_initial_contact = models.BooleanField(default=False)
    score = models.FloatField(null=True)

    class Meta:
        ordering = ("project", "-student_is_initial_contact", "student")

    def __str__(self) -> str:
        return f"{self.project.pid}{self.project_instance.number}: {self.student.name2}"
