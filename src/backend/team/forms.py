from django.forms import ModelForm

from .models import Team


class TeamForm(ModelForm):
    class Meta:
        model = Team
        fields = ("url_repository", "url_project", "url_miro", "coach_name", "coach_email")
