from random import shuffle

from itertools import groupby
from django.utils import timezone
from django.db.models import F

from app.models import Project, Student, Settings, Info
from poll.models import POLL_SCORES, Poll, ProjectAnswer
from poll.helper import (
    get_poll_stats_for_student,
    get_project_ids_with_score_ordered,
    get_happiness_icon,
)

from .models import ProjectInstance, Team
from .algorithm import AssignmentAlgo


# Stores the ID mappings between database (model) and algorithm.
id_mapper = {
    "student": {
        "db2algo": {},  # student id    (database)  : student index (algorithm)
        "algo2db": {},  # student index (algorithm) : student id    (database)
    },
    "project": {
        "db2algo": {},  # project id    (database)  : project index (algorithm)
        "algo2db": {},  # project index (algorithm) : project id    (database)
    },
}


def get_prepared_project_instance_ids() -> list:
    """
    Returns a list of the IDs of the created project instances,
    sorted by the total score of the projects.

    Projects with the same score are shuffled.

    NOTE: Each call deletes and recreates the project instances.
          Can only be used if no teams exist.
    """

    settings = Settings.load()

    # 1. Gets the project IDs with scores ordered by the total score (descending).
    projects = get_project_ids_with_score_ordered()

    # 2. Groups the projects per total score.
    projects_per_score = {}
    for score, projects_in_score in groupby(projects, lambda x: x["total_score"]):
        projects_per_score[score] = list(projects_in_score)

    # 3. Shuffles the projects with the same score.
    for score in dict(filter(lambda x: len(x[1]) > 1, projects_per_score.items())):
        shuffle(projects_per_score[score])

    # 4. Creates the final list of projects.
    # - ordered by the total score (descending)
    # - projects with the same score are shuffled
    # - use only the project IDs and the total scores
    projects = []
    for _, projects_in_score in projects_per_score.items():
        for project in projects_in_score:
            projects.append({"project": project["project"], "score": project["total_score"]})

    # 5. Clears existing project instances.
    ProjectInstance.objects.all().delete()

    # 6. Creates the project instances and a list of project instance IDs
    #    from the list of projects.
    project_instance_ids = []
    for project in projects:
        project_object = Project.objects.get(id=project["project"])
        # Sets the number of instances to the project or the default setting.
        n_instances = settings.project_instances if project_object.instances is None else project_object.instances
        # Creates the project instances and adds the IDs (PKs) to a list.
        for idx in range(1, n_instances + 1):
            project_instance = ProjectInstance.objects.create(number=idx, project=project_object)
            project_instance_ids.append(project_instance.pk)

    return project_instance_ids


def set_db_algo_id_mappings(students: list, project_instances: list):
    """
    Maps the IDs of the students and projects from the database
    to the algorithm and vice versa.
    """

    # Updates the mappings of student IDs.
    id_mapper["student"]["db2algo"].clear()
    id_mapper["student"]["algo2db"].clear()
    for i in range(len(students)):
        id_mapper["student"]["db2algo"][students[i]["id"]] = i
        id_mapper["student"]["algo2db"][i] = students[i]["id"]

    # Updates the mappings of project IDs.
    id_mapper["project"]["db2algo"].clear()
    id_mapper["project"]["algo2db"].clear()
    for i in range(len(project_instances)):
        id_mapper["project"]["db2algo"][project_instances[i]["id"]] = i
        id_mapper["project"]["algo2db"][i] = project_instances[i]["id"]


def get_prepared_data_per_student(students: list[dict], project_instances: list[dict], project_answers: list[dict]):
    project_instance_answers_per_student = {}
    data_per_student = {}
    # student_infos = {}

    # Sets the project instance answers per student.
    # Every project instance gets the same answers like the project answers.
    for student_id, project_answers_for_student in groupby(project_answers, lambda x: x["student"]):
        project_answers_per_student = list(project_answers_for_student)
        project_instance_answers = {}
        student_data = {
            # "student_infos": {},
            "is_wing": False,
            "project_answers": {},
        }

        for project_answer in project_answers_per_student:
            p_instances = list(filter(lambda x: x["project"] == project_answer["project"], project_instances))
            for p_instance in p_instances:
                project_instance_answers[id_mapper["project"]["db2algo"].get(p_instance["id"])] = project_answer[
                    "score"
                ]

        if len(project_instance_answers) > 0:
            project_instance_answers_per_student[id_mapper["student"]["db2algo"].get(student_id)] = (
                project_instance_answers
            )
            student_data["project_answers"] = project_instance_answers
            data_per_student[id_mapper["student"]["db2algo"].get(student_id)] = student_data

    # Creates the student infos.
    for student in students:
        # student_infos[id_mapper["student"]["db2algo"].get(student["id"])] = int(student["is_wing"])
        data_per_student[id_mapper["student"]["db2algo"].get(student["id"])]["is_wing"] = int(student["is_wing"])

    return data_per_student


def prepare_data_per_student(project_instance_ids):
    # Sets the students data: student_id, is_wing.
    students_data = []
    students = Student.objects.all()
    for student in students:
        students_data.append({"id": student.pk, "is_wing": student.is_wing})
    # students_data = list(Student.objects.values("id", "is_wing"))  # keyword 'is_wing' is not a field in Student

    # Sets the project instances data: project_instance_id, project_id.
    project_instances_data = list(ProjectInstance.objects.filter(id__in=project_instance_ids).values("id", "project"))

    # Sets the project answers data: student_id, project_id, score.
    project_answers_data = list(
        ProjectAnswer.objects.order_by("poll").values("project", "score", student=F("poll__student"))
    )

    # Prepares the data for the algorithm.
    set_db_algo_id_mappings(students_data, project_instances_data)
    data_per_student = get_prepared_data_per_student(students_data, project_instances_data, project_answers_data)

    return data_per_student


def generate_teams_with_algorithm(data_per_student):
    settings = Settings.load()

    max_scores = {
        "project": POLL_SCORES["max"],
    }

    algo = AssignmentAlgo(data_per_student, max_scores, settings.team_min_member)
    algo.run()
    result = algo.get_result()

    return result


def save_teams(algo_result):
    teams = []

    for a in algo_result:
        project_instance_id = id_mapper["project"]["algo2db"].get(a[0])
        student_id = id_mapper["student"]["algo2db"].get(a[1])
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
    project_instance_ids = get_prepared_project_instance_ids()
    data_per_student = prepare_data_per_student(project_instance_ids)

    result = generate_teams_with_algorithm(data_per_student)
    save_teams(result)
    set_initial_project_leaders()


def get_prepared_teams_for_view():
    settings = Settings.load()
    # data = []
    data = {
        "teams": [],
        "happiness": {
            "summary": "",
        },
    }

    total_student_count = 0
    total_happiness_score = 0
    total_happiness_poll_score = 0

    project_instances = ProjectInstance.objects.filter(team__isnull=False).values_list("id", flat=True).distinct()
    for project_instance in project_instances:
        data_set = {
            "project_instance": ProjectInstance.objects.get(id=project_instance),
            "students": [],
            "student_active_count": 0,
            "emails": [],
            "happiness": {},
        }
        team_happiness_score = 0
        team_happiness_poll_score = 0

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

            # Sets the css classes.
            if student["is_initial_contact"]:
                student["css_classes"].append("fw-semibold")
            if not student["is_visible"]:
                student["css_classes"].append("text-decoration-line-through")
            if student["is_out"]:
                student["css_classes"].append("text-danger")
            elif not student["is_visible"]:
                student["css_classes"].append("text-secondary")

            # Adds the email and increases active count only for active (visible) students.
            if student["is_visible"]:
                data_set["emails"].append(team.student.email)
                data_set["student_active_count"] += 1

            # Adds the student.
            data_set["students"].append(student)

            # Summarizes the students happiness scores in the team.
            team_happiness_score += student["stats"]["happiness"]["total"]
            team_happiness_poll_score += student["stats"]["happiness"]["poll"]["total"]

        # Sets the number of students in the team.
        student_count = len(data_set["students"])
        total_student_count += student_count

        # Summarizes the happiness scores of all teams.
        total_happiness_score += team_happiness_score
        total_happiness_poll_score += team_happiness_poll_score

        # Sets the average happiness scores of the team.
        team_happiness_score = round(team_happiness_score / student_count, 2)
        team_happiness_poll_score = round(team_happiness_poll_score / student_count, 2)

        # Set happiness icon
        happiness_total_icon = get_happiness_icon(team_happiness_score)

        # Adds the happiness summary per team.
        data_set["happiness"] = {
            "summary": f"{happiness_total_icon} <strong>{team_happiness_score}</strong> ({team_happiness_poll_score})"
        }

        # Adds the data per team.
        data["teams"].append(data_set)

    # Sets the average happiness scores of all teams.
    if total_student_count > 0:
        total_happiness_score = round(total_happiness_score / total_student_count, 2)
        total_happiness_poll_score = round(total_happiness_poll_score / total_student_count, 2)

    # Adds the happiness summary of all teams.
    data["happiness"] = {
        "summary": f"{get_happiness_icon(total_happiness_score)} <strong>{total_happiness_score}</strong> ({total_happiness_poll_score})"
    }

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
