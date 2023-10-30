import datetime

from django.db.models import Sum, Avg, Min, Max

from app.models import Student, Project, Role, Info
from .models import POLL_SCORES, Poll, ProjectAnswer, RoleAnswer


def prepare_poll_data_from_post(student, POST, projects, roles):
    poll_data = {"student": student, "project": {}, "role": {}}

    # set default poll scores
    for project in projects:
        poll_data["project"][str(project.id)] = {
            "project": project,
            "score": POLL_SCORES["default"],
        }
    for role in roles:
        poll_data["role"][str(role.id)] = {
            "role": role,
            "score": POLL_SCORES["default"],
        }

    # set new poll scores
    for post in POST:
        parts = post.split("_")
        if len(parts) == 3 and parts[2] == "score":
            object_name = str(parts[0])
            object_id = str(parts[1])
            object_score = int(POST.get(post, POLL_SCORES["default"]))
            if object_name in ["project", "role"]:
                if object_id in poll_data[object_name]:
                    poll_data[object_name][object_id]["score"] = object_score

    return poll_data


def save_poll_data_to_db(student, POST, projects, roles):
    # prepare poll data from POST
    poll_data = prepare_poll_data_from_post(student, POST, projects, roles)

    # save poll
    values = {
        "is_generated": False,
    }
    poll, created = Poll.objects.update_or_create(
        student=poll_data["student"],
        defaults=values,
    )

    # save project answers
    for id in poll_data["project"]:
        values = {
            "score": poll_data["project"][id]["score"],
        }
        ProjectAnswer.objects.update_or_create(
            poll=poll,
            project=poll_data["project"][id]["project"],
            defaults=values,
        )

    # save role answers
    for id in poll_data["role"]:
        values = {
            "score": poll_data["role"][id]["score"],
        }
        RoleAnswer.objects.update_or_create(
            poll=poll,
            role=poll_data["role"][id]["role"],
            defaults=values,
        )

    # save update time (TODO)DateTimeField
    values = {
        "polls_last_update": datetime.datetime.now()
    }
    Info.objects.update_or_create(defaults=values)


def load_poll_data_for_form(student, projects, roles):
    poll_data = {"projects": [], "roles": []}

    poll = Poll.objects.filter(student=student).first()

    if poll:
        project_answers = ProjectAnswer.objects.filter(poll=poll)
        role_answers = RoleAnswer.objects.filter(poll=poll)

        for answer in project_answers:
            poll_data["projects"].append({"project": answer.project, "score": answer.score})
        for answer in role_answers:
            poll_data["roles"].append({"role": answer.role, "score": answer.score})
    else:
        for project in projects:
            poll_data["projects"].append({"project": project, "score": POLL_SCORES["default"]})
        for role in roles:
            poll_data["roles"].append({"role": role, "score": POLL_SCORES["default"]})

    return poll_data


def generate_poll_data_for_students_without_poll():
    polls = Poll.objects.all()
    projects = Project.objects.all()
    roles = Role.objects.all()
    default = POLL_SCORES["default"]
    students_without_answers = Student.objects.filter(poll__isnull=True)
    projects_without_answers = Project.objects.filter(projectanswer__isnull=True)
    roles_without_answers = Role.objects.filter(roleanswer__isnull=True)

    for student in students_without_answers:
        poll = Poll.objects.create(
            student=student,
            is_generated=True,
        )
        for project in projects:
            ProjectAnswer.objects.create(poll=poll, project=project, score=default)
        for role in roles:
            RoleAnswer.objects.create(poll=poll, role=role, score=default)

    for project in projects_without_answers:
        for poll in polls:
            ProjectAnswer.objects.create(poll=poll, project=project, score=default)

    for role in roles_without_answers:
        for poll in polls:
            RoleAnswer.objects.create(poll=poll, role=role, score=default)


def get_project_ids_with_score_ordered():
    return (
        ProjectAnswer.objects.values("project")
        .annotate(total_score=Sum("score"), avg_score=Avg("score"))
        .order_by("-total_score")
    )


def get_poll_stats_for_student(team):
    student_id = team.student.id
    project_id = team.project.id
    role_id = team.role.id

    # TODO:
    # - check if poll or answers exist
    poll = Poll.objects.get(student=student_id)

    # extract stats
    project_score = ProjectAnswer.objects.get(poll=poll, project=project_id).score
    project_score_sum = ProjectAnswer.objects.filter(poll=poll).aggregate(Sum("score"))["score__sum"]
    project_score_avg = ProjectAnswer.objects.filter(poll=poll).aggregate(Avg("score"))["score__avg"]
    project_score_min = ProjectAnswer.objects.filter(poll=poll).aggregate(Min("score"))["score__min"]
    project_score_max = ProjectAnswer.objects.filter(poll=poll).aggregate(Max("score"))["score__max"]

    role_score = RoleAnswer.objects.get(poll=poll, role=role_id).score
    role_score_sum = RoleAnswer.objects.filter(poll=poll).aggregate(Sum("score"))["score__sum"]
    role_score_avg = RoleAnswer.objects.filter(poll=poll).aggregate(Avg("score"))["score__avg"]
    role_score_min = RoleAnswer.objects.filter(poll=poll).aggregate(Min("score"))["score__min"]
    role_score_max = RoleAnswer.objects.filter(poll=poll).aggregate(Max("score"))["score__max"]

    # prepare result
    poll_stats = {
        "project": {
            "score": project_score,
            "sum": project_score_sum,
            "avg": round(project_score_avg, 2),
            "min": project_score_min,
            "max": project_score_max,
        },
        "role": {
            "score": role_score,
            "sum": role_score_sum,
            "avg": round(role_score_avg, 2),
            "min": role_score_min,
            "max": role_score_max,
        },
        "happiness": {},
        "happiness_icon": "",
        "summary": "",
    }

    # Set happiness scores
    poll_stats["happiness"] = calc_happiness_score(poll_stats)

    # Set happiness icon
    score = poll_stats["happiness"]["total"]
    poll_stats["happiness_icon"] = get_happiness_icon(score)

    # Set summary text
    text_total = (
        f"Total: <strong>{poll_stats['happiness']['total']}</strong> ({poll_stats['happiness']['poll']['total']})"
    )
    text_project = (
        f"Project: <strong>{poll_stats['happiness']['project']}</strong> ({poll_stats['happiness']['poll']['project']})"
    )
    text_role = f"Role: <strong>{poll_stats['happiness']['role']}</strong> ({poll_stats['happiness']['poll']['role']})"
    poll_stats["summary"] = f"{poll_stats['happiness_icon']} {text_total}, {text_project}, {text_role}"

    return poll_stats


def calc_happiness_score(scores):
    # gains are from algorithm
    # TODO: seaparte it and use it here and in the algorithm
    project_gain = 0.8
    role_gain = 0.2

    # TODO: get from POLL_SCORES
    max_score = 5

    # calc each happiness
    # - normalize score (1-5 -> 0-4) to (0-1) like algorithm

    # Happiness with max possible poll scores
    # - use max score 5 from POLL_SCORES
    project_hs = (scores["project"]["score"] - 1) / (max_score - 1)
    role_hs = (scores["role"]["score"] - 1) / (max_score - 1)

    # Happiness with own poll scores
    # - use individual max score
    project_poll_hs = (scores["project"]["score"] - 1) / (scores["project"]["max"] - 1)
    role_poll_hs = (scores["role"]["score"] - 1) / (scores["role"]["max"] - 1)

    # calc total happiness
    total_hs = project_gain * project_hs + role_gain * role_hs
    total_poll_hs = project_gain * project_poll_hs + role_gain * role_poll_hs

    # prepare result
    happiness = {
        "total": round(total_hs, 2),
        "project": round(project_hs, 2),
        "role": round(role_hs, 2),
        "poll": {
            "total": round(total_poll_hs, 2),
            "project": round(project_poll_hs, 2),
            "role": round(role_poll_hs, 2),
        },
    }

    return happiness


def get_happiness_icon(score):
    # get poll score
    poll_score = POLL_SCORES["choices"][0]  # very bad
    if score > 0.8:
        poll_score = POLL_SCORES["choices"][4]  # very good
    elif score > 0.6:
        poll_score = POLL_SCORES["choices"][3]  # good
    elif score > 0.4:
        poll_score = POLL_SCORES["choices"][2]  # neutral
    elif score > 0.2:
        poll_score = POLL_SCORES["choices"][1]  # bad

    # set icon with color
    icon = '<i class="bu bi-' + poll_score["icon"] + '-fill" style="color:' + poll_score["color"] + '"></i>'

    return icon