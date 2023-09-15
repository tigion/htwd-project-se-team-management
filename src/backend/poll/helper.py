from app.models import Student, Project, Role
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
    poll, created = Poll.objects.update_or_create(
        student=poll_data["student"],
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


def load_poll_data_for_form(student, projects, roles):
    poll_data = {"projects": [], "roles": []}

    poll = Poll.objects.filter(student=student).first()

    if poll:
        project_answers = ProjectAnswer.objects.filter(poll=poll)
        role_answers = RoleAnswer.objects.filter(poll=poll)

        for answer in project_answers:
            poll_data["projects"].append(
                {"project": answer.project, "score": answer.score}
            )
        for answer in role_answers:
            poll_data["roles"].append({"role": answer.role, "score": answer.score})
    else:
        for project in projects:
            poll_data["projects"].append(
                {"project": project, "score": POLL_SCORES["default"]}
            )
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
