from itertools import groupby
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
            project_instance_total_scores.append({"project": project_instance.pk, "score": project["score"]})

    # for x in project_instance_total_scores:
    #     project = ProjectInstance.objects.get(id=x["project"])
    #     print(f"> {x} {project.piid}")

    # limit needed projects
    # 1. calc needed project count
    project_count = int(Student.objects.count() / settings.team_min_member)
    if project_count < 1:
        project_count = 1
    # 2. cut unneeded projects
    # project_instance_total_scores = project_instance_total_scores[:project_count]

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
    project_instance_answers_per_student = {}
    student_infos = {}
    data_per_student = {}

    # Updates the project keys keymap.
    key_mapper["project"]["db2algo"].clear()
    key_mapper["project"]["algo2db"].clear()
    for i in range(len(project_instances)):
        key_mapper["project"]["db2algo"][project_instances[i][0]] = i
        key_mapper["project"]["algo2db"][i] = project_instances[i][0]

    # Updates the student keys keymap.
    key_mapper["student"]["db2algo"].clear()
    key_mapper["student"]["algo2db"].clear()
    for i in range(len(students)):
        key_mapper["student"]["db2algo"][students[i][0]] = i
        key_mapper["student"]["algo2db"][i] = students[i][0]

    # Creates the project instance answers per student.
    # Every project instance gets the same answers like the project answers.
    for key, g in groupby(project_answers, lambda x: x[0]):  # x[0] is student key
        p_answers_per_s = list(g)
        p_instance_answers = {}
        tmp = {
            "is_wing": False,
            "project_answers": {},
        }
        for i in range(len(p_answers_per_s)):
            p_instances = list(filter(lambda x: x[1] == p_answers_per_s[i][1], project_instances))
            for p_instance in p_instances:
                p_instance_answers[key_mapper["project"]["db2algo"].get(p_instance[0])] = p_answers_per_s[i][2]
        if len(p_instance_answers) > 0:
            project_instance_answers_per_student[key_mapper["student"]["db2algo"].get(key)] = p_instance_answers
            tmp["project_answers"] = p_instance_answers
            data_per_student[key_mapper["student"]["db2algo"].get(key)] = tmp

    # Creates the student infos.
    for student in students:
        student_infos[key_mapper["student"]["db2algo"].get(student[0])] = int(student[1])
        data_per_student[key_mapper["student"]["db2algo"].get(student[0])]["is_wing"] = int(student[1])

    return data_per_student


def prepare_data(project_instance_ids):
    # Sets the students data: student_id, is_wing.
    students_data = []
    students = Student.objects.all()
    for student in students:
        students_data.append((student.pk, student.is_wing))

    # Sets the project instances data: project_instance_id, project_id.
    project_instances_data = list(
        ProjectInstance.objects.filter(id__in=project_instance_ids).values_list("id", "project")
    )

    # Sets the project answers data: student_id, project_id, score.
    project_answers_data = list(ProjectAnswer.objects.order_by("poll").values_list("poll__student", "project", "score"))

    # Prepares the data for the algorithm.
    data_per_student = map_keys_and_prepare_data(students_data, project_instances_data, project_answers_data)

    return data_per_student


def generate_teams_with_algorithm(data_per_student):
    settings = Settings.load()
    max_scores = {
        "project": POLL_SCORES["max"],
    }

    algo = AssignmentAlgo(
        data_per_student,
        max_scores,
        settings.team_min_member,
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

        project_id = ProjectInstance.objects.get(id=project_instance_id).project.pk
        team = Team(
            project_id=project_id,
            project_instance_id=project_instance_id,
            student_id=student_id,
            student_is_initial_contact=False,
            score=score,
        )
        teams.append(team)

    Team.objects.bulk_create(teams)

    # Saves the update time.
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
    data_per_student = prepare_data(project_instance_ids)

    result = generate_teams_with_algorithm(data_per_student)
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
