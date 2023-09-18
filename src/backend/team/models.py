from django.db import models
from app.models import Project, Student, Role


# Create your models here.


class Team(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    student = models.OneToOneField(Student, on_delete=models.PROTECT, unique=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    score = models.FloatField(null=True)

    # class Meta:
    #     unique_together = ["project", "student"]
    class Meta:
        ordering = ("project", "role", "student")

    def __str__(self) -> str:
        return f"{self.project.pid}: {self.student.name2} - {self.role.name}"