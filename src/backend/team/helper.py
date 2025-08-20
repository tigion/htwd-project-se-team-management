from itertools import groupby
from django.db.models import Sum
from random import shuffle
from django.utils import timezone

from app.models import Project, Student, Settings, Info
from poll.models import POLL_SCORES, Poll, ProjectAnswer
from poll.helper import (
    get_poll_stats_for_student,
    get_project_ids_with_score_ordered,
    get_happiness_icon,
)

from .models import ProjectInstance, Team
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
}


def prepare_project_instances():
    # TODO: Needs refactoring

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

    # create project instances
    ProjectInstance.objects.all().delete()
    project_instance_total_scores = []
    for project in project_total_scores:
        project_object = Project.objects.get(id=project["project"])
        max_range = settings.project_instances
        if project_object.instances is not None:
            max_range = project_object.instances
        for i in range(1, max_range + 1):
            project_instance = ProjectInstance.objects.create(number=i, project=project_object)
            project_instance_total_scores.append({"project": project_instance.id, "score": project["score"]})

    # for x in project_instance_total_scores:
    #     project = ProjectInstance.objects.get(id=x["project"])
    #     print(f"> {x} {project.piid}")

    # limit needed projects
    # 1. calc needed project count
    project_count = int(Student.objects.count() / settings.team_min_member)
    if project_count < 1:
        project_count = 1
    # 2. cut unneeded projects
    project_instance_total_scores = project_instance_total_scores[:project_count]

    # for x in project_instance_total_scores:
    #     print(f"> {x}")

    # create project instances id list
    pi_ids = []
    for project_instance in project_instance_total_scores:
        pi_ids.append(project_instance["project"])

    # print(f"> Project IDs: {ids}")

    return pi_ids


def map_keys_and_prepare_data(
    students: list,
    project_instances: list,
    project_answers: list,
):
    def student_key(x):
        return x[0]

    result_project_answers = {}
    result_wing_answers = {}

    # update project_keys keymap
    key_mapper["project"]["db2algo"].clear()
    key_mapper["project"]["algo2db"].clear()
    for i in range(len(project_instances)):
        key_mapper["project"]["db2algo"][project_instances[i][0]] = i
        key_mapper["project"]["algo2db"][i] = project_instances[i][0]

    # print("-----------------------------------------")
    # print(f"> {key_mapper['project']}")
    # for temp in key_mapper["project"]:
    #     print(f"> project key mapper - {temp}: {key_mapper['project'][temp]}")

    # update student_keys keymap
    key_mapper["student"]["db2algo"].clear()
    key_mapper["student"]["algo2db"].clear()
    for i in range(len(students)):
        key_mapper["student"]["db2algo"][students[i][0]] = i
        key_mapper["student"]["algo2db"][i] = students[i][0]

    # print("-----------------------------------------")
    # print(f"> {key_mapper['student']}")

    # print("-----------------------------------------")
    # print(f"> {project_instances}")
    # print("-----------------------------------------")
    # print(f"> {project_answers}")
    # create project_answers with grouped db2algo keys
    for key, g in groupby(project_answers, student_key):
        group = list(g)
        # print("-----------------------------------------")
        # print(f"> group: {group}")
        d = {}
        for i in range(len(group)):
            pis = list(filter(lambda x: x[1] == group[i][1], project_instances))
            for pi in pis:
                d[key_mapper["project"]["db2algo"].get(pi[0])] = group[i][2]
        if len(d) > 0:
            result_project_answers[key_mapper["student"]["db2algo"].get(key)] = d

    # create wing_answers
    for student in students:
        result_wing_answers[key_mapper["student"]["db2algo"].get(student[0])] = int(student[1])

    result = {
        "project_answers": result_project_answers,
        # "role_answers": result_role_answers,
        "wing_answers": result_wing_answers,
    }
    # print("-----------------------------------------")
    # print(f"> {result}")
    return result


def prepare_data(project_instance_ids):
    # students: student_id, is_wing
    students = []
    temp_students = Student.objects.all()
    for ts in temp_students:
        students.append((ts.id, ts.is_wing))

    # project instances: project_instance_id, project_id
    project_instances = list(ProjectInstance.objects.filter(id__in=project_instance_ids).values_list("id", "project"))

    # project_answers: student_id, project_id, score
    project_answers = list(ProjectAnswer.objects.order_by("poll").values_list("poll__student", "project", "score"))

    # prepare data for algorithm
    data = map_keys_and_prepare_data(students, project_instances, project_answers)

    return data


def generate_teams_with_algorithm(data):
    max_scores = {
        "project": POLL_SCORES["max"],
    }

    algo = AssignmentAlgo(
        data.get("project_answers"),
        data.get("wing_answers"),
        max_scores,
    )
    algo.run()
    result = algo.get_result()

    return result


def save_teams(algo_result):
    teams = []

    for a in algo_result:
        project_instance_id = key_mapper["project"]["algo2db"].get(a[0])
        student_id = key_mapper["student"]["algo2db"].get(a[1])
        score = a[2]

        project_id = ProjectInstance.objects.get(id=project_instance_id).project.id
        team = Team(
            project_id=project_id,
            project_instance_id=project_instance_id,
            student_id=student_id,
            student_is_initial_contact=False,
            score=score,
        )
        teams.append(team)

    Team.objects.bulk_create(teams)

    # save update time
    values = {"teams_last_update": timezone.now()}
    Info.objects.update_or_create(defaults=values)


def set_initial_project_leaders():
    """Sets a random project leader for each project."""

    project_instances = ProjectInstance.objects.filter(team__isnull=False).values_list("id", flat=True).distinct()
    for project_instance in project_instances:
        teams = Team.objects.filter(project_instance=project_instance).order_by("?")
        if len(teams) > 0:
            teams[0].student_is_initial_contact = True
            teams[0].save()


def generate_teams():
    # TODO: check needed data and tables
    # - min count for algorithm?
    Team.objects.all().delete()
    if not Poll.objects.exists() or not ProjectAnswer.objects.exists():
        return

    # TODO: Needs refactoring
    #       - projects with answers -> project instances -> data
    project_instance_ids = prepare_project_instances()
    data = prepare_data(project_instance_ids)

    result = generate_teams_with_algorithm(data)
    save_teams(result)
    set_initial_project_leaders()


def get_prepared_teams_for_view():
    settings = Settings.load()
    data = []

    project_instances = ProjectInstance.objects.filter(team__isnull=False).values_list("id", flat=True).distinct()
    for project_instance in project_instances:
        data_set = {
            "project_instance": ProjectInstance.objects.get(id=project_instance),
            "students": [],
            "student_active_count": 0,
            "emails": [],
            "happiness": {},
        }
        happiness_total_score = 0
        happiness_poll_total_score = 0

        teams = Team.objects.filter(project_instance=project_instance)
        for team in teams:
            student = {
                "name": team.student.name,
                "study_program_short": team.student.study_program_short,
                "is_initial_contact": team.student_is_initial_contact,
                "is_wing": team.student.is_wing,
                "is_active": team.student.is_active,
                "is_out": team.student.is_out,
                "score": team.score,  # score from algorithm
                "stats": get_poll_stats_for_student(team),
                "is_visible": False if team.student.is_out or team.student.is_wing and settings.wings_are_out else True,
                "css_classes": [],
            }

            # set css classes
            if student["is_initial_contact"]:
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
