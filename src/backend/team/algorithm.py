"""
This module implements the assignment algorithm that assigns students
to projects as optimally as possible based on their survey responses.
"""

import math

from ortools.sat.python import cp_model


class AssignmentAlgo:
    """
    Calculates the optimal assignment of students to projects
    based on their survey responses.

    The assignment algorithm is implemented with the CP-SAT solver
    from Google OR-Tools. This is a constraint solver that allows
    rules to be defined in the form of hard and soft constraints.

    - Hard constraints are conditions that must be met.
      - `__add_hc_one_project_per_student()`
      - `__add_hc_students_assigned_equally()`
      - `__add_hc_wing_students_assigned_equally()`
      - `__add_hc_number_used_projects_equals_number_required()`

    - Soft constraints evaluate the quality of a potential solution.
      - `__add_sc_maximize_project_score()`

    Sources:
    - https://developers.google.com/optimization/
    - https://medium.com/data-science/where-you-should-drop-deep-learning-in-favor-of-constraint-solvers-eaab9f11ef45
    """

    def __init__(
        self,
        data_per_student: dict[int, dict],
        # data_per_student: dict[int, dict[str, int | dict[int, int]]],
        max_scores: dict[str, int],
        min_students_per_project: int,
    ):
        """
        The constructor of the assignment algorithm.

        Args:
            data_per_student: The data per student. Includes the wing flag and project answers.
            max_scores: The maximum scores.
            min_students_per_project: The minimum number of students per project.
        """

        # Sets the given data.
        self.__data_per_student = data_per_student
        self.__max_project_score = max_scores["project"]

        # Extracts the project and student ids.
        self.__student_ids = list(self.__data_per_student.keys())
        self.__project_ids = []
        if len(self.__student_ids) > 1:
            first_student_data = self.__data_per_student[self.__student_ids[0]]
            self.__project_ids = list(first_student_data.get("project_answers", {}).keys())

        # Sets the number of projects, students and wing students.
        self.__n_students = len(self.__student_ids)
        self.__n_projects = len(self.__project_ids)
        self.__n_wing_students = len(dict(filter(lambda x: x[1]["is_wing"], self.__data_per_student.items())))

        # Sets the min number of students per project.
        self.__min_students_per_project = min_students_per_project

        # Sets the number of projects required.
        self.__n_projects_required = math.floor(self.__n_students / self.__min_students_per_project)

        # Checks if the number of projects required is greater than the number of possible projects.
        if self.__n_projects_required > self.__n_projects:
            # Corrects the number of projects required.
            self.__n_projects_required = self.__n_projects
            # Corrects the min number of students per project.
            self.__min_students_per_project = math.floor(self.__n_students / self.__n_projects_required)

        # Sets the max number of students per project.
        self.__max_students_per_project = self.__min_students_per_project
        if self.__n_students % self.__min_students_per_project != 0:
            self.__max_students_per_project += 1

        # Sets the limit (min and max) of wings per project.
        self.__min_wings_per_project = math.floor(self.__n_wing_students / self.__n_projects_required)
        self.__max_wings_per_project = math.ceil(self.__n_wing_students / self.__n_projects_required)

        # The maximum runtime of the solver in seconds.
        self.__max_runtime = 60

        # Indicates whether the algorithm has already been executed and a result exists.
        self.__has_result = False

        # Creates the model.
        self.__model = cp_model.CpModel()

        # The model variables.
        self.__model_x = {}

        # The result.
        self.__result: list[tuple[int, int, int]] = []

    def __init_model_variables(self):
        """
        Creates a dictionary which contains OR-Tools bool 0-1 variables for
        every possible combination of project and student.

        The value of a bool 0-1 variable, for example `[(4,2)]`, means the following:
        - `0` (`False`) ... The student with id `2` is not in project with id `4`.
        - `1` (`True`) ... The student with id `2` is in project with id `4`.
        """

        for p_id in self.__project_ids:
            for s_id in self.__student_ids:
                self.__model_x[(p_id, s_id)] = self.__model.NewBoolVar("(%d, %d)" % (p_id, s_id))

    def __add_hc_one_project_per_student(self):
        """
        Adds the following hard constraints to the model:
        - A student is assigned to exactly one project.
        """

        for s_id in self.__student_ids:
            student_projects = []
            for p_id in self.__project_ids:
                student_projects.append(self.__model_x[(p_id, s_id)])
            self.__model.Add(sum(student_projects) == 1)

    def __add_hc_students_assigned_equally(self):
        """
        Adds the following hard constraints to the model:
        - Students are assigned equally to projects.
        - Number of students per project should be 0 or between min and max.
        """

        for p_id in self.__project_ids:
            project_students = []
            for s_id in self.__student_ids:
                project_students.append(self.__model_x[(p_id, s_id)])

            # Number of students should be 0 or between min and max.
            b = self.__model.NewBoolVar("b")
            self.__model.Add(sum(project_students) == 0).OnlyEnforceIf(b.Not())
            self.__model.Add(sum(project_students) >= self.__min_students_per_project).OnlyEnforceIf(b)
            self.__model.Add(sum(project_students) <= self.__max_students_per_project).OnlyEnforceIf(b)

    def __add_hc_wing_students_assigned_equally(self):
        """
        Adds the following hard constraints to the model:
        - Wing students are assigned equally to projects.
        """

        for p_id in self.__project_ids:
            project_wing_students = []
            for s_id in self.__student_ids:
                if self.__data_per_student[s_id]["is_wing"]:
                    project_wing_students.append(self.__model_x[(p_id, s_id)])

            # Number of wings should be between min and max.
            self.__model.Add(sum(project_wing_students) >= self.__min_wings_per_project)
            self.__model.Add(sum(project_wing_students) <= self.__max_wings_per_project)

    def __add_hc_number_used_projects_equals_number_required(self):
        """
        Adds the following hard constraints to the model:
        - Number of used projects should be the number of required projects.
        """

        used_projects_count = 0
        for p_id in self.__project_ids:
            project_students = []
            for s_id in self.__student_ids:
                project_students.append(self.__model_x[(p_id, s_id)])
            has_students = self.__model.NewBoolVar("has_students")
            self.__model.Add(sum(project_students) == 0).OnlyEnforceIf(has_students.Not())
            self.__model.Add(sum(project_students) > 0).OnlyEnforceIf(has_students)
            used_projects_count += has_students

        self.__model.Add(used_projects_count == self.__n_projects_required)

    def __add_sc_maximize_project_score(self):
        """
        Adds the following soft constraints to the model:
        - Maximizes the assignment scores of the students.

        The higher the value, the better the match with the student's preferences.
        """

        soft_constraints = []
        for p_id in self.__project_ids:
            for s_id in self.__student_ids:
                score = self.__get_total_score(p_id, s_id)
                soft_constraints.append(score * self.__model_x[(p_id, s_id)])

        self.__model.Maximize(sum(soft_constraints))

    def __extract_solution(self, solver: cp_model.CpSolver):
        """
        Extracts all successful assignments between projects and students,
        including their scores in the `self.__result` list.

        Successful assignments are those where the result is `1` (`True`).

        Args:
            solver: The constraint solver.
        """

        self.__result = []
        for p_id in self.__project_ids:
            for s_id in self.__student_ids:
                if solver.Value(self.__model_x[(p_id, s_id)]) == 1:
                    score = self.__get_total_score(p_id, s_id)
                    self.__result.append((p_id, s_id, score))

    def __normalize_score(self, answer_score: int) -> int:
        """
        Normalizes the given score to a value between 0 and 100.

        Args:
            answer_score: The score to normalize.
        """
        # Decreases the score by 1 to start with 0.
        score = answer_score - 1
        max_score = self.__max_project_score - 1

        # Normalizes the answer score to be between 0 and 100.
        score = score * 100 / max_score

        return int(score)

    def __get_normalized_project_score(self, project: int, answers: dict[int, int]) -> int:
        """
        Returns the normalized project score for the given project and answers.

        Args:
            project: The project id.
            answers: The project answers.
        """

        return self.__normalize_score(answers.get(project) or 0)

    def __get_total_score(self, project: int, student: int) -> int:
        """
        Returns the total score for the given project and student.

        Args:
            project: The project id.
            student: The student id.

        This may be necessary in order to weight multiple scores
        with a gain factor to one total score in the future.
        - `0.8 * project_score + 0.2 * x_score`
        """

        project_score = self.__get_normalized_project_score(
            project, self.__data_per_student[student]["project_answers"]
        )
        score = project_score

        return score

    def run(self):
        """
        Initializes needed variables, adds the hard and soft constraints,
        starts the solver and extracts the results.

        The function blocks until the calculation is finished or aborted.

        The calculation is stopped if
        - an optimal result was found,
        - the given task/function is not solvable or
        - the max runtime was exceeded. In this case, the best solution
          found will be used.

        Raises:
            AssignmentAlgoException: If the equation cannot be solved for the given data, or the time has expired.
        """

        # Initializes all possible combinations of project and student.
        self.__init_model_variables()

        # Adds the hard constraints.
        self.__add_hc_one_project_per_student()
        self.__add_hc_students_assigned_equally()
        self.__add_hc_wing_students_assigned_equally()
        self.__add_hc_number_used_projects_equals_number_required()

        # Adds the soft constraints.
        self.__add_sc_maximize_project_score()

        # Creates the solver.
        solver = cp_model.CpSolver()

        # Sets the time limit for the solver.
        solver.parameters.max_time_in_seconds = self.__max_runtime

        # Solves the equation.
        self.__has_result = False
        status = solver.Solve(self.__model)
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # Extracts the solution.
            self.__extract_solution(solver)
            self.__has_result = True
        else:
            raise AssignmentAlgoException("The equation cannot be solved for the given data, or the time has expired.")

    def get_result(self) -> list[tuple[int, int, int]]:
        """
        Returns the result of the assignment as a list of tuples
        if the algorithm has already been executed.

        Raises:
            AssignmentAlgoException: If the result is accessed before the algorithm has been executed.
        """

        if not self.__has_result:
            raise AssignmentAlgoException("Tried to access result before it was run.")
        else:
            return self.__result

    # TODO: Not used yet. Later, the max runtime should be set by the user.
    #
    # def set_max_runtime(self, max_runtime: int):
    #     assert type(max_runtime) is int
    #     self.__max_runtime = max_runtime
    #
    # def get_max_runtime(self):
    #     return self.__max_runtime


class AssignmentAlgoException(Exception):
    """Exception, which is thrown by the *AssignmentAlgo* class."""

    pass
