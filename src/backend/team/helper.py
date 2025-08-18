from itertools import groupby
from django.db.models import Sum
from random import shuffle
from django.utils import timezone

# from app.models import Project, Student, Role, Settings, Info
from app.models import Project, Student, Settings, Info
from poll.models import Poll, ProjectAnswer

# from poll.models import Poll, ProjectAnswer, RoleAnswer
from poll.helper import (
    get_poll_stats_for_student,
    get_project_ids_with_score_ordered,
    get_happiness_icon,
)

from .models import Team
from .algorithm import AssignmentAlgo


# stores key mappings between database (model) and algorithm
key_mapper = {
    "project": {
        "db2algo": {},  # project id    (database)  : project index (algorithm)
        "algo2db": {},  # project index (algorithm) : project id    (database)
    },
    "student": {
        "db2algo": {},  # student id    (database)  : student index (algorithm)
        "algo2db": {},  # student index (algorithm) : student id    (database)
    },
    # "role": {
    #     "db2algo": {},  # role id    (database)  : role index (algorithm)
    #     "algo2db": {},  # role index (algorithm) : role id    (database)
    # },
}


def prepare_projects():
    settings = Settings.load()

    # shuffle projects with same score
    # 1. create list with projects and total scores
    project_total_scores = get_project_ids_with_score_ordered()
    # 2. group projects with same score
    projects_per_score = {}
    for project in project_total_scores:
        if project["total_score"] in projects_per_score:
            projects_per_score[project["total_score"]].append(project["project"])
        else:
            projects_per_score[project["total_score"]] = [project["project"]]
    # 3. shuffle projects with same score
    for score in projects_per_score:
        if len(projects_per_score[score]) > 1:
            shuffle(projects_per_score[score])
    # 4. rebuild
    project_total_scores = []
    for score in projects_per_score:
        for project in projects_per_score[score]:
            project_total_scores.append({"project": project, "score": score})

    # for x in project_total_scores:
    #     print(f"> {x}")

    # limit needed projects
    # 1. calc needed project count
    project_count = int(Student.objects.count() / settings.team_min_member)
    if project_count < 1:
        project_count = 1
    # 2. cut unneeded projects
    project_total_scores = project_total_scores[:project_count]

    # for x in project_total_scores:
    #     print(f"> {x}")

    # create project_id list
    ids = []
    for project in project_total_scores:
        ids.append(project["project"])

    # print(f"> Project IDs: {ids}")

    return ids


def map_keys_and_prepare_data(
    projects: list,
    students: list,
    # roles: list,
    project_answers: list,
    # role_answers: list,
):
    def student_key(x):
        return x[0]

    result_project_answers = {}
    # result_role_answers = {}
    result_wing_answers = {}

    # update project_keys keymap
    key_mapper["project"]["db2algo"].clear()
    key_mapper["project"]["algo2db"].clear()
    for i in range(len(projects)):
        key_mapper["project"]["db2algo"][projects[i][0]] = i
        key_mapper["project"]["algo2db"][i] = projects[i][0]

    # for temp in key_mapper["project"]:
    #     print(f"> project key mapper - {temp}: {key_mapper['project'][temp]}")

    # update student_keys keymap
    key_mapper["student"]["db2algo"].clear()
    key_mapper["student"]["algo2db"].clear()
    for i in range(len(students)):
        key_mapper["student"]["db2algo"][students[i][0]] = i
        key_mapper["student"]["algo2db"][i] = students[i][0]

    # # update role_keys keymap
    # key_mapper["role"]["db2algo"].clear()
    # key_mapper["role"]["algo2db"].clear()
    # for i in range(len(roles)):
    #     key_mapper["role"]["db2algo"][roles[i][0]] = i
    #     key_mapper["role"]["algo2db"][i] = roles[i][0]

    # create project_answers with grouped db2algo keys
    for key, g in groupby(project_answers, student_key):
        group = list(g)
        d = {}
        for i in range(len(group)):
            d[key_mapper["project"]["db2algo"].get(group[i][1])] = group[i][2]
        result_project_answers[key_mapper["student"]["db2algo"].get(key)] = d

    # # create role_answers with grouped db2algo keys
    # for key, g in groupby(role_answers, student_key):
    #     group = list(g)
    #     d = {}
    #     for i in range(len(group)):
    #         d[key_mapper["role"]["db2algo"].get(group[i][1])] = group[i][2]
    #     result_role_answers[key_mapper["student"]["db2algo"].get(key)] = d

    # create wing_answers
    for student in students:
        result_wing_answers[key_mapper["student"]["db2algo"].get(student[0])] = int(student[1])

    result = {
        "project_answers": result_project_answers,
        # "role_answers": result_role_answers,
        "wing_answers": result_wing_answers,
    }
    return result


def prepare_data(project_ids):
    # students: student_id, is_wing
    students = []
    temp_students = Student.objects.all()
    for ts in temp_students:
        students.append((ts.id, ts.is_wing))

    # projects: project_id
    projects = list(Project.objects.filter(id__in=project_ids).values_list("id"))

    # projects: project_id
    # roles = list(Role.objects.values_list("id"))

    # project_answers: poll_id, project_id, score
    project_answers = list(
        ProjectAnswer.objects.filter(project__in=project_ids)
        .order_by("poll")
        .values_list("poll__student", "project", "score")
    )

    # role_answers: poll_id, role_id, score
    # role_answers = list(RoleAnswer.objects.order_by("poll").values_list("poll__student", "role", "score"))

    # prepare data for algorithm
    data = map_keys_and_prepare_data(projects, students, project_answers)
    # data = map_keys_and_prepare_data(projects, students, roles, project_answers, role_answers)

    return data


def generate_teams_with_algorithm(data):
    max_scores = {
        # TODO: get max scores from POLL_SCORES
        "project": 5,
        "role": 5,
    }

    algo = AssignmentAlgo(
        data.get("project_answers"),
        # data.get("role_answers"),
        data.get("wing_answers"),
        max_scores,
    )
    algo.run()
    result = algo.get_result()

    return result


def save_teams(algo_result):
    teams = []
    for a in algo_result:
        project_id = key_mapper["project"]["algo2db"].get(a[0])
        student_id = key_mapper["student"]["algo2db"].get(a[1])
        # role_id = key_mapper["role"]["algo2db"].get(a[2])
        score = a[2]
        # score = a[3]

        # print(f"-> key map {a}: {project_id} {student_id} {role_id} - {score}")

        team = Team(
            project_id=project_id,
            student_id=student_id,
            # role_id=role_id,
            score=score,
        )
        teams.append(team)

    Team.objects.bulk_create(teams)

    # save update time
    values = {"teams_last_update": timezone.now()}
    Info.objects.update_or_create(defaults=values)


def generate_teams():
    # TODO: check needed data and tables
    # - min count for algorithm?
    Team.objects.all().delete()
    if not Poll.objects.exists() or not ProjectAnswer.objects.exists():
        return
    # if not Poll.objects.exists() or not ProjectAnswer.objects.exists() or not RoleAnswer.objects.exists():
    #     return

    project_ids = prepare_projects()
    data = prepare_data(project_ids)
    result = generate_teams_with_algorithm(data)
    save_teams(result)


def get_prepared_teams_for_view():
    settings = Settings.load()
    data = []

    projects = Project.objects.filter(team__isnull=False).values_list("id", flat=True).distinct()
    for project in projects:
        data_set = {
            "project": Project.objects.get(id=project),
            "students": [],
            "student_active_count": 0,
            "emails": [],
            "happiness": {},
        }
        happiness_total_score = 0
        happiness_poll_total_score = 0

        teams = Team.objects.filter(project=project)
        for team in teams:
            student = {
                "name": team.student.name,
                # "role": team.role,
                "is_project_leader": False,
                "is_wing": team.student.is_wing,
                "is_active": team.student.is_active,
                "is_out": team.student.is_out,
                "score": team.score,  # score from algorithm
                "stats": get_poll_stats_for_student(team),
                "is_visible": False if team.student.is_out or team.student.is_wing and settings.wings_are_out else True,
                "css_classes": [],
            }

            # set css classes
            if student["is_project_leader"]:
                student["css_classes"].append("fw-semibold")
            if not student["is_visible"]:
                student["css_classes"].append("text-decoration-line-through")
            if student["is_out"]:
                student["css_classes"].append("text-danger")
            elif not student["is_visible"]:
                student["css_classes"].append("text-secondary")

            # add email and increase active count only for active (visible) students
            if student["is_visible"]:
                data_set["emails"].append(team.student.email)
                data_set["student_active_count"] += 1

            # add student
            data_set["students"].append(student)

            # summarize student happiness scores
            happiness_total_score = happiness_total_score + student["stats"]["happiness"]["total"]
            happiness_poll_total_score = happiness_poll_total_score + student["stats"]["happiness"]["poll"]["total"]

        # set student count in team
        student_count = len(data_set["students"])

        # average team happiness scores
        happiness_total_score = round(happiness_total_score / student_count, 2)
        happiness_poll_total_score = round(happiness_poll_total_score / student_count, 2)

        # Set happiness icon
        happiness_total_icon = get_happiness_icon(happiness_total_score)

        # add happiness summary
        data_set["happiness"] = {
            "summary": f"{happiness_total_icon} <strong>{happiness_total_score}</strong> ({happiness_poll_total_score})"
        }

        # add data per team
        data.append(data_set)

    return data


# def generate_teams_simple():
#     # simple check of needed data
#     Team.objects.all().delete()
#     if (
#         not Project.objects.exists()
#         or not Student.objects.exists()
#         or not Role.objects.exists()
#     ):
#         return
#
#     # get needed settings
#     settings = Settings.load()
#     min_member = settings.team_min_member
#
#     # calc needed project count
#     project_count = int(Student.objects.count() / min_member)
#
#     # for all students without team
#     while Student.objects.filter(team__isnull=True).exists():
#         # for all needed projects
#         for project in Project.objects.all()[:project_count]:
#             # note minimum team members
#             is_empty_team = True
#             if Team.objects.filter(project=project).exists():
#                 min_member = 1
#                 is_empty_team = False
#             for i in range(min_member):
#                 if Student.objects.filter(team__isnull=True).exists():
#                     # get new random student without team
#                     student = (
#                         Student.objects.filter(team__isnull=True).order_by("?").first()
#                     )
#
#                     # set first student as project leader
#                     if i == 0 and is_empty_team:
#                         role = Role.objects.first()
#                     else:
#                         role = Role.objects.exclude(id=1).order_by("?").first()
#
#                     # add team member
#                     Team.objects.create(
#                         project=project,
#                         student=student,
#                         role=role,
#                     )
