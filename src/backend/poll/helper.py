from django.utils import timezone

from django.db.models import Sum, Avg, Min, Max

from app.models import Student, Project, Info, DevSettings
from .models import POLL_SCORES, POLL_LEVELS, Poll, ProjectAnswer, LevelAnswer

import random


def prepare_poll_data_from_post(student, POST, projects):
    """
    Returns the prepared poll data from POST for the specified
    student and projects.
    """

    poll_data = {
        "student": student,
        "project": {},
        "level": POLL_LEVELS["default"],
    }

    # Sets the default poll scores.
    for project in projects:
        poll_data["project"][str(project.id)] = {
            "project": project,
            "score": POLL_SCORES["default"],
        }

    # Sets the selected project scores and the selected student level.
    for post in POST:
        parts = post.split("_")
        # Sets the project score.
        if parts[0] == "project":
            id = str(parts[1])
            if id in poll_data["project"]:
                poll_data["project"][id]["score"] = int(POST.get(post, POLL_SCORES["default"]))
        # Sets the student level.
        elif parts[0] == "student" and parts[1] == "level":
            poll_data["level"] = int(POST.get(post, POLL_LEVELS["default"]))

    return poll_data


def save_poll_data_to_db(student, POST, projects):
    """
    Saves the prepared poll data from POST for the specified
    student and projects.
    """

    # Prepares the poll data from POST.
    poll_data = prepare_poll_data_from_post(student, POST, projects)

    # Saves the poll data.
    values = {
        "is_generated": False,
    }
    poll, _created = Poll.objects.update_or_create(
        student=poll_data["student"],
        defaults=values,
    )

    # Saves the project answers.
    for id in poll_data["project"]:
        values = {
            "score": poll_data["project"][id]["score"],
        }
        ProjectAnswer.objects.update_or_create(
            poll=poll,
            project=poll_data["project"][id]["project"],
            defaults=values,
        )

    # Saves the level answer.
    values = {
        "level": poll_data["level"],
    }
    LevelAnswer.objects.update_or_create(
        poll=poll,
        defaults=values,
    )

    # Saves the update time.
    values = {"polls_last_update": timezone.now()}
    Info.objects.update_or_create(defaults=values)


def load_poll_data_for_form(student, projects):
    """
    Returns the required poll data for the specified student
    and project for the form.

    If the student has no poll, the default scores are used.
    """
    poll_data = {
        "projects": [],
        "level": POLL_LEVELS["default"],
    }
    poll = Poll.objects.filter(student=student).first()

    if poll:
        # Uses the project answers from the database.
        project_answers = ProjectAnswer.objects.filter(poll=poll)
        for answer in project_answers:
            poll_data["projects"].append({"project": answer.project, "score": answer.score})
        # Uses the level answer from the database.
        student_level_answer = LevelAnswer.objects.filter(poll=poll).first()
        if student_level_answer is not None:
            poll_data["level"] = student_level_answer.level
    else:
        # Uses the default project answer scores. if no poll exists.
        for project in projects:
            poll_data["projects"].append({"project": project, "score": POLL_SCORES["default"]})

    return poll_data


def generate_poll_data_for_students_without_poll():
    """
    Generates the poll data for all students without a poll.

    Uses for the project answers the default score or optionally
    random scores.
    """

    dev_settings = DevSettings.load()
    polls = Poll.objects.all()
    projects = Project.objects.all()
    students_without_answers = Student.objects.filter(poll__isnull=True)
    projects_without_answers = Project.objects.filter(projectanswer__isnull=True)

    for student in students_without_answers:
        poll = Poll.objects.create(
            student=student,
            is_generated=True,
        )
        for project in projects:
            ProjectAnswer.objects.create(
                poll=poll,
                project=project,
                score=(
                    POLL_SCORES["default"]
                    if not dev_settings.use_random_poll_defaults
                    else random.randint(
                        POLL_SCORES["min"] if project.pid != "A" else POLL_SCORES["min"] + 2,
                        POLL_SCORES["max"] if project.pid != "B" else POLL_SCORES["max"] - 2,
                    )
                ),
            )
        random_level = 3
        x = random.randint(1, 20)
        if x < 10:
            random_level = 3
        elif x < 15:
            random_level = 2
        elif x < 19:
            random_level = 1
        else:
            random_level = 4
        LevelAnswer.objects.create(
            poll=poll,
            level=(
                POLL_LEVELS["default"] if not dev_settings.use_random_poll_defaults else random_level
                # else random.randint(POLL_LEVELS["min"], POLL_LEVELS["max"])
            ),
        )

    for project in projects_without_answers:
        for poll in polls:
            ProjectAnswer.objects.create(
                poll=poll,
                project=project,
                score=(
                    POLL_SCORES["default"]
                    if not dev_settings.use_random_poll_defaults
                    else random.randint(POLL_SCORES["min"], POLL_SCORES["max"])
                ),
            )


def get_number_of_students_per_level() -> dict:
    """
    Returns the number of students per level.
    """

    n_students_per_level = {}
    for level in POLL_LEVELS["choices"]:
        n_students_per_level[level] = LevelAnswer.objects.filter(level=level).count()

    return n_students_per_level


def get_project_ids_ordered_by_score():
    """
    Returns a list of project ids with the total score and
    average score ordered by the total score.
    """

    project_ids = (
        ProjectAnswer.objects.values("project")
        .annotate(total_score=Sum("score"), avg_score=Avg("score"))
        .order_by("-total_score")
    )

    return project_ids


def get_poll_stats_for_student(team) -> dict:
    """
    Returns the poll stats for the given team entry.

    A team entry is a student and a project.

    Args:
        team: The team entry.
    """

    # Gets the student and project ids.
    student_id = team.student.id
    project_id = team.project.id

    # Uses the project answer scores if the poll for the student exists
    # otherwise uses the default score.
    if Poll.objects.filter(student=student_id).exists():
        # Uses the project answer scores.
        poll = Poll.objects.get(student=student_id)
        project_score = ProjectAnswer.objects.get(poll=poll, project=project_id).score
        project_score_sum = ProjectAnswer.objects.filter(poll=poll).aggregate(Sum("score"))["score__sum"]
        project_score_avg = ProjectAnswer.objects.filter(poll=poll).aggregate(Avg("score"))["score__avg"]
        project_score_min = ProjectAnswer.objects.filter(poll=poll).aggregate(Min("score"))["score__min"]
        project_score_max = ProjectAnswer.objects.filter(poll=poll).aggregate(Max("score"))["score__max"]
        level = LevelAnswer.objects.get(poll=poll).level
    else:
        # Uses the default score.
        default_score = POLL_SCORES["default"]
        project_score = default_score
        project_score_sum = default_score
        project_score_avg = default_score
        project_score_min = default_score
        project_score_max = default_score
        level = POLL_LEVELS["default"]

    # Prepares the result.
    poll_stats = {
        "project": {
            "score": project_score,
            "sum": project_score_sum,
            "avg": round(project_score_avg, 2),
            "min": project_score_min,
            "max": project_score_max,
        },
        "level": POLL_LEVELS["choices"][level],
        "happiness": {},
        "happiness_icon": "",
        "summary": "",
    }

    # Sets the happiness scores.
    poll_stats["happiness"] = calc_happiness_score(poll_stats)

    # Sets the happiness icon.
    score = poll_stats["happiness"]["total"]
    poll_stats["happiness_icon"] = get_happiness_icon(score)

    # Sets the summary text.
    text_total = (
        f"Total: <strong>{poll_stats['happiness']['total']}</strong> ({poll_stats['happiness']['poll']['total']})"
    )
    # text_project = (
    #     f"Project: <strong>{poll_stats['happiness']['project']}</strong> ({poll_stats['happiness']['poll']['project']})"
    # )
    # poll_stats["summary"] = f"{poll_stats['happiness_icon']} {text_total}, {text_project}"
    poll_stats["summary"] = f"{poll_stats['happiness_icon']} {text_total}"

    return poll_stats


def calc_happiness_score(scores: dict) -> dict:
    """
    Calculates the total, project and own poll scores for the given scores.

    Normalizes the integer scores from 1-5 to 0-4 and calculates
    the happiness to a float between 0 and 1 like the algorithm.

    Args:
        scores: The scores.

    Returns:
        The happiness score.
    """

    max_score = POLL_SCORES["max"]

    # Gains are from algorithm
    #
    # NOTE: The gains are not used yet. Possibly, they will be used in the future.
    #
    # TODO: Separate the gains and use it here and in the algorithm
    #       or get it from the algorithm.
    #
    # project_gain = 0.8
    # role_gain = 0.2

    # Calculates the happiness score with the max possible poll scores.
    # - Normalizes the score 1-5 -> 0-4 to 0-1 like algorithm.
    if max_score == 1:
        project_hs = 0
    else:
        project_hs = (scores["project"]["score"] - 1) / (max_score - 1)

    # Calculates the happiness score with the own individual max poll scores.
    # - Normalizes the score 1-5 -> 0-4 to 0-1 like algorithm.
    if scores["project"]["max"] == 1:
        project_poll_hs = 0
    else:
        project_poll_hs = (scores["project"]["score"] - 1) / (scores["project"]["max"] - 1)

    # Calculates the total happiness.
    total_hs = project_hs
    total_poll_hs = project_poll_hs
    # total_hs = project_gain * project_hs
    # total_poll_hs = project_gain * project_poll_hs

    # Prepares the happiness data.
    happiness = {
        "total": round(total_hs, 2),
        "project": round(project_hs, 2),
        "poll": {
            "total": round(total_poll_hs, 2),
            "project": round(project_poll_hs, 2),
        },
    }

    return happiness


def get_happiness_icon(score: float) -> str:
    """
    Returns the HTML string with the icon and color for the given score.

    Args:
        score: The score.
    """

    # Gets the poll score infos.
    if score > 0.8:
        poll_score = POLL_SCORES["choices"][5]  # very good
    elif score > 0.6:
        poll_score = POLL_SCORES["choices"][4]  # good
    elif score > 0.4:
        poll_score = POLL_SCORES["choices"][3]  # neutral
    elif score > 0.2:
        poll_score = POLL_SCORES["choices"][2]  # bad
    else:
        poll_score = POLL_SCORES["choices"][1]  # very bad

    # Sets the icon with color as HTML string.
    icon = '<i class="bu bi-' + poll_score["icon"] + '-fill" style="color:' + poll_score["color"] + '"></i>'

    return icon
