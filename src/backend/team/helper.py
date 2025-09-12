from itertools import groupby
from django.utils import timezone
from django.db.models import F, Sum

from app.models import Project, Student, Settings, DevSettings, Info
from poll.models import POLL_SCORES, POLL_LEVELS, Poll, ProjectAnswer, LevelAnswer
from poll.helper import (
    get_poll_stats_for_student,
    get_happiness_icon,
)

from .models import ProjectInstance, Team
from .algorithm import AssignmentAlgorithm


# Stores the ID to index mappings between database (model) and algorithm.
id_idx_mappings = {
    "student": {
        "db2algo": {},  # student id    (database)  : student index (algorithm)
        "algo2db": {},  # student index (algorithm) : student id    (database)
    },
    "project": {
        "db2algo": {},  # project id    (database)  : project index (algorithm)
        "algo2db": {},  # project index (algorithm) : project id    (database)
    },
}


def clean_up():
    """
    Deletes all existing teams and recreates the project instances.
    """

    Team.objects.all().delete()
    recreate_project_instances()

    values = {
        "teams_last_update": None,
        "result_info": None,
    }
    Info.objects.update_or_create(defaults=values)


def recreate_project_instances():
    """
    Recreates the project instances for all projects.

    NOTE: Each call deletes and creates the project instances.
          Can only be used if no teams exist.
    """

    settings = Settings.load()
    projects = Project.objects.all().order_by("pid")

    # Deletes the existing project instances.
    ProjectInstance.objects.all().delete()

    for project in projects:
        # Sets the number of instances to the project or the default setting.
        n_instances = settings.project_instances if project.instances is None else project.instances

        # Creates the project instances.
        project_instances = []
        for idx in range(1, n_instances + 1):
            project_instances.append(ProjectInstance(project=project, number=idx))
        ProjectInstance.objects.bulk_create(project_instances)


def get_project_instance_ids() -> list:
    """
    Returns a list of the project instances IDs.
    """

    # NOTE: There are various variants to test the effect on the algorithm.
    #       It seems that the order does not matter.

    # Variant 1:
    # Returns IDs in default order.
    project_instances = list(ProjectInstance.objects.all().values_list("id", flat=True))

    # Variant 2:
    # Returns IDs ordered by project and number (same as default order).
    # project_instances = list(ProjectInstance.objects.all().order_by("project", "number").values_list("id", flat=True))

    # Variant 3:
    # Returns IDs ordered by total score, project and number.
    # project_instances = list(
    #     ProjectInstance.objects.annotate(total_score=Sum("project__projectanswer__score"))
    #     .order_by("-total_score", "project", "number")
    #     .values_list("id", flat=True)
    # )

    # Variant 4:
    #  Returns IDs in random order.
    # project_instances = list(ProjectInstance.objects.all().order_by("?").values_list("id", flat=True))

    return project_instances


def create_id_idx_mappings(students: list, project_instances: list):
    """
    Maps the IDs of the students and project instances from the database
    to the algorithm indexes and vice versa.
    """

    # TODO: Use the IDs directly instead of the indexes. So no need to map.

    # Sets the mappings of student IDs.
    id_idx_mappings["student"]["db2algo"].clear()
    id_idx_mappings["student"]["algo2db"].clear()
    for idx in range(len(students)):
        id_idx_mappings["student"]["db2algo"][students[idx]["id"]] = idx
        id_idx_mappings["student"]["algo2db"][idx] = students[idx]["id"]

    # Sets the mappings of project IDs.
    id_idx_mappings["project"]["db2algo"].clear()
    id_idx_mappings["project"]["algo2db"].clear()
    for idx in range(len(project_instances)):
        id_idx_mappings["project"]["db2algo"][project_instances[idx]["id"]] = idx
        id_idx_mappings["project"]["algo2db"][idx] = project_instances[idx]["id"]


def create_data_per_student(
    students: list[dict], project_instances: list[dict], project_answers: list[dict], level_answers: list[dict]
) -> dict:
    """
    Returns the prepared data per student for the algorithm.

    ```python
    {
        <student_id>: {
            "is_wing": bool,
            "project_answers": {
                <project_instance_id>: <score>,
                ...
            },
            "level_answer": int,
        },
        ...
    }
    ```

    Args:
        students: The list of students.
        project_instances: The list of project instances.
        project_answers: The list of project answers.
        level_answers: The list of level answers.
    """

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
            "level_answer": POLL_LEVELS["default"],
        }

        for project_answer in project_answers_per_student:
            p_instances = list(filter(lambda x: x["project"] == project_answer["project"], project_instances))
            for p_instance in p_instances:
                project_instance_answers[id_idx_mappings["project"]["db2algo"].get(p_instance["id"])] = project_answer[
                    "score"
                ]

        if len(project_instance_answers) > 0:
            project_instance_answers_per_student[id_idx_mappings["student"]["db2algo"].get(student_id)] = (
                project_instance_answers
            )
            student_data["project_answers"] = project_instance_answers
            data_per_student[id_idx_mappings["student"]["db2algo"].get(student_id)] = student_data

    # Creates the student infos.
    for student in students:
        # student_infos[id_mapper["student"]["db2algo"].get(student["id"])] = int(student["is_wing"])
        data_per_student[id_idx_mappings["student"]["db2algo"].get(student["id"])]["is_wing"] = int(student["is_wing"])

    # Sets the level answers.
    for level_answer in level_answers:
        data_per_student[id_idx_mappings["student"]["db2algo"].get(level_answer["student"])]["level_answer"] = (
            level_answer["level"]
        )

    return data_per_student


def create_data_for_algorithm() -> dict:
    """
    Creates the data for the algorithm.

    Returns:
        The data for the algorithm.
    """

    # Sets the students data: student_id, is_wing.
    students_data = []

    # Variant 1: Students in default order.
    students = Student.objects.all()
    # Variant 2: Students in random order.
    # students = Student.objects.order_by("?").all()

    for student in students:
        students_data.append({"id": student.pk, "is_wing": student.is_wing})
    # students_data = list(Student.objects.values("id", "is_wing"))  # keyword 'is_wing' is not a field in Student

    # Sets the project instances data: project_instance_id, project_id.
    project_instance_ids = get_project_instance_ids()
    project_instances_data = list(ProjectInstance.objects.filter(id__in=project_instance_ids).values("id", "project"))

    # Sets the project answers data: student_id, project_id, score.
    project_answers_data = list(
        ProjectAnswer.objects.order_by("poll").values("project", "score", student=F("poll__student"))
    )

    level_answers_data = list(LevelAnswer.objects.values("level", student=F("poll__student")))

    # Prepares the data for the algorithm.
    create_id_idx_mappings(students_data, project_instances_data)
    data = create_data_per_student(students_data, project_instances_data, project_answers_data, level_answers_data)

    return data


def generate_teams_with_algorithm() -> dict:
    """
    Generates the teams with the algorithm and returns the result.

    Returns:
        The results of the algorithm.
    """

    settings = Settings.load()
    dev_settings = DevSettings.load()

    # Creates the data for the algorithm.
    data = create_data_for_algorithm()

    # Sets the needed options.
    opts = {
        "max_project_score": POLL_SCORES["max"],
        "min_students_per_project": settings.team_min_member,
        "assignment_variant": dev_settings.assignment_variant,
        "max_runtime": dev_settings.max_runtime,
        "relative_gap_limit": dev_settings.relative_gap_limit,
        "num_workers": dev_settings.num_workers,
    }

    result = {
        "assignments": [],
        "info": {},
    }
    if not AssignmentAlgorithm.get_is_running():
        # Creates and initializes the algorithm with the given data and options.
        algorithm = AssignmentAlgorithm(data, opts)
        # Runs the algorithm to find an optimal assignment of students to projects.
        algorithm.run()
        # Gets the results.
        result = algorithm.get_result()

    return result


def save_teams_to_db(result):
    """
    Saves the generated teams in the result to the database.

    Args:
        result: The result of the algorithm.
    """

    assignments = result["assignments"] or []
    info = result["info"] or {}
    project_instance_counts = {}
    teams = []

    # Creates the team objects with project instance numbers in sequential order.
    for instance_idx, assignments_per_instance_idx in groupby(assignments, lambda x: x[0]):
        assignments_per_instance_idx = list(assignments_per_instance_idx)

        # Gets the project instance ID.
        project_instance_id = id_idx_mappings["project"]["algo2db"].get(instance_idx)

        # Gets the project ID of the project instance object.
        project_id = ProjectInstance.objects.get(id=project_instance_id).project.pk

        # Counts the project instances per project.
        if project_id not in project_instance_counts:
            project_instance_counts[project_id] = 1
        else:
            project_instance_counts[project_id] += 1

        # Gets the next project instance ID.
        new_project_instance_id = ProjectInstance.objects.get(
            project=project_id, number=project_instance_counts[project_id]
        ).pk

        # Creates the team objects per project instance.
        for result in assignments_per_instance_idx:
            # Gets the student ID.
            student_id = id_idx_mappings["student"]["algo2db"].get(result[1])
            # Gets the score.
            score = result[2]
            # Creates the team object.
            team = Team(
                project_id=project_id,
                project_instance_id=new_project_instance_id,
                student_id=student_id,
                student_is_initial_contact=False,
                score=score,
            )
            # Adds the team object to the list.
            teams.append(team)

    # Saves the team objects.
    Team.objects.bulk_create(teams)

    # Saves the result info.
    result_infos = []
    for key in info:
        result_infos.append(f"{key}: {info[key]}")
    result_info = "\n".join(result_infos)
    values = {
        "teams_last_update": timezone.now(),
        "result_info": result_info,
    }
    Info.objects.update_or_create(defaults=values)


def set_initial_project_leaders():
    """
    Sets a random project leader for each project.
    """

    project_instances = ProjectInstance.objects.filter(team__isnull=False).values_list("id", flat=True).distinct()
    for project_instance in project_instances:
        teams = Team.objects.filter(project_instance=project_instance).order_by("?")
        if len(teams) > 0:
            teams[0].student_is_initial_contact = True
            teams[0].save()


def generate_teams() -> bool:
    """
    Generates the teams.

    Returns:
        True if the teams were generated successfully, False otherwise.
    """

    # Cleans up the existing teams and project instances.
    clean_up()

    # Checks if polls and project answers exist.
    # If not, the teams cannot be generated.
    if not Poll.objects.exists() or not ProjectAnswer.objects.exists():
        return False

    # Generates the teams with the algorithm.
    result = generate_teams_with_algorithm()

    # Saves the teams to the database.
    save_teams_to_db(result)

    # Sets the initial project leaders.
    set_initial_project_leaders()

    return True


def get_teams_for_view() -> dict:
    """
    Returns the prepared teams for the view.
    """

    settings = Settings.load()

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
        total_happiness_score = round(total_happiness_score / total_student_count, 3)
        total_happiness_poll_score = round(total_happiness_poll_score / total_student_count, 3)

    # Adds the happiness summary of all teams.
    data["happiness"] = {
        "summary": f"{get_happiness_icon(total_happiness_score)} <strong>{total_happiness_score}</strong> ({total_happiness_poll_score})"
    }

    return data
