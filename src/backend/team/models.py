from app.models import Project, Student
from django.db import models

# Create your models here.


class ProjectInstance(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    number = models.IntegerField()

    class Meta:
        # unique_together = ("project", "number")  # may be deprecated in the future
        constraints = (models.UniqueConstraint(fields=["project", "number"], name="unique_project_number"),)
        ordering = ("project", "number")

    @property
    def piid(self):
        return f"{self.project.pid}{self.number}"

    def __str__(self) -> str:
        return f"{self.piid}"


class Team(models.Model):
    project_instance = models.OneToOneField(ProjectInstance, on_delete=models.PROTECT, primary_key=True)
    url_repository = models.URLField(blank=True, null=True, verbose_name="Link zum GitHub Repository")
    url_project = models.URLField(blank=True, null=True, verbose_name="Link zum GitHub Project")
    url_miro = models.URLField(blank=True, null=True, verbose_name="Link zum Miro Board")
    coach_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name des Coaches")
    coach_email = models.EmailField(blank=True, null=True, verbose_name="E-Mail des Coaches")

    class Meta:
        ordering = ("project_instance",)

    def __str__(self) -> str:
        return f"{self.project_instance}"


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    student = models.OneToOneField(Student, on_delete=models.PROTECT, unique=True)
    student_is_initial_contact = models.BooleanField(default=False)
    score = models.FloatField(null=True)

    class Meta:
        ordering = ("team__project_instance", "-student_is_initial_contact", "student")

    def __str__(self) -> str:
        return f"{self.team.project_instance}: {self.student.name2}"
