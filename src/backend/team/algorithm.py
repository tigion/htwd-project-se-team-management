"""
This module implements the assignment algorithm that assigns students
to projects as optimally as possible based on their survey responses.
"""

import math
import datetime
import logging

from ortools.sat.python import cp_model

from django.conf import settings


class AssignmentAlgorithm:
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

    # Indicates whether the algorithm is running.
    __is_running = False

    def __init__(self, data: dict[int, dict], opts: dict):
        """
        The constructor of the assignment algorithm.

        Args:
            data: The data per student. Includes the wing flag and project answers.
            opts: The options for the algorithm.

        The options are:
            `max_project_score`: The maximum project score.
            `min_students_per_project`: The minimum number of students per project.
        """

        # Sets the given data.
        self.__data_per_student = data
        # Sets the maximum project score.
        self.__max_project_score = opts["max_project_score"]
        # Sets the assignment variant.
        self.__assignment_variant = opts["assignment_variant"]
        # The maximum runtime of the solver in seconds.
        self.__max_runtime = opts["max_runtime"]
        # Sets the relative gap limit.
        self.__relative_gap_limit = opts["relative_gap_limit"]
        # Sets the number of workers.
        self.__num_workers = opts["num_workers"]

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
        self.__min_students_per_project = opts["min_students_per_project"]

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

        # Creates the model.
        self.__model = cp_model.CpModel()

        # The model variables.
        self.__model_x = {}

        # Indicates whether the algorithm has already been executed and a result exists.
        self.__has_result = False

        # The results.
        self.__results: list[tuple[int, int, int]] = []

        # The information about the result of the solver.
        self.__result_info: dict = {}

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
                self.__model_x[(p_id, s_id)] = self.__model.new_bool_var(f"({p_id}, {s_id})")

    def __add_hc_one_project_per_student(self):
        """
        Adds the following hard constraints to the model:
        - A student is assigned to exactly one project.
        """

        for s_id in self.__student_ids:
            student_projects = []
            for p_id in self.__project_ids:
                student_projects.append(self.__model_x[(p_id, s_id)])
            self.__model.add(sum(student_projects) == 1)

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
            project_hast_students1 = self.__model.new_bool_var("project_hast_students1")
            self.__model.add(sum(project_students) == 0).only_enforce_if(project_hast_students1.Not())
            self.__model.add(sum(project_students) >= self.__min_students_per_project).only_enforce_if(
                project_hast_students1
            )
            self.__model.add(sum(project_students) <= self.__max_students_per_project).only_enforce_if(
                project_hast_students1
            )

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
            if self.__min_wings_per_project == self.__max_wings_per_project:
                # FIX: Error with min team members eqals to max team members.

                # self.__model.add(sum(project_wing_students) == 1)
                # self.__model.add(sum(project_wing_students) == self.__min_wings_per_project)
                # self.__model.add(sum(project_wing_students) >= self.__min_wings_per_project)
                # self.__model.add(sum(project_wing_students) <= self.__max_wings_per_project + 1)
                pass
            else:
                self.__model.add(sum(project_wing_students) >= self.__min_wings_per_project)
                self.__model.add(sum(project_wing_students) <= self.__max_wings_per_project)

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

            project_has_students2 = self.__model.new_bool_var("project_has_students2")
            self.__model.add(sum(project_students) == 0).only_enforce_if(project_has_students2.Not())
            self.__model.add(sum(project_students) > 0).only_enforce_if(project_has_students2)
            used_projects_count += project_has_students2

        self.__model.add(used_projects_count == self.__n_projects_required)

    def __add_hc_no_level_24(self):
        # FIX: Add fallback if one project with level 2 and level 4 must be existing.

        for p_id in self.__project_ids:
            students_per_level = {1: [], 2: [], 3: [], 4: []}
            for s_id in self.__student_ids:
                level = self.__data_per_student[s_id]["level_answer"]
                students_per_level[level].append(self.__model_x[(p_id, s_id)])

            has_level_2 = self.__model.new_bool_var("has_level_2")
            self.__model.add(sum(students_per_level[2]) < 1).only_enforce_if(has_level_2.Not())
            self.__model.add(sum(students_per_level[2]) >= 1).only_enforce_if(has_level_2)

            has_level_4 = self.__model.new_bool_var("has_level_4")
            self.__model.add(sum(students_per_level[4]) < 1).only_enforce_if(has_level_4.Not())
            self.__model.add(sum(students_per_level[4]) >= 1).only_enforce_if(has_level_4)

            self.__model.add(has_level_4 + has_level_2 < 2)

    def __add_sc_maximize_project_score(self):
        """
        Adds the following soft constraints to the model:
        - Maximizes the assignment scores of the students.
        - TODO: Testing variants of level impact.

        The higher the value, the better the match with the student's preferences.
        """

        soft_constraints = []
        for p_id in self.__project_ids:
            used_projects_per_student_level = {1: [], 2: [], 3: [], 4: []}
            p_levels = {1: [], 2: [], 3: [], 4: []}  # Variant 1: The students per level.
            p_students = []
            for s_id in self.__student_ids:
                # Gets the score (poll wish) for the given project and student.
                # score = self.__get_total_score(p_id, s_id)
                score = self.__get_total_score(p_id, s_id)

                # TODO: Testing variants of level impact.
                #
                # Variants:
                # 1: [S ] Score, no level impact.
                # 2: [ L] Level, no score impact.
                # 3: [SL] Level and score impact.
                # 4: [SL] Score with level impact.
                #         Raises/lowers the higher scores and lowers/raises the lower scores.

                # Variant 4:
                if self.__assignment_variant == 3:
                    factors = {1: 0, 2: 1, 3: 0, 4: -1}
                    level = self.__data_per_student[s_id]["level_answer"]
                    factor = factors[level]
                    if score > 50 and factor != 0:
                        score += factor
                    elif score < 50 and factor != 0:
                        score -= factor

                # Variant 1, 3, 4:
                if self.__assignment_variant in [1, 3, 4]:
                    # Adds the score per project and student to the soft constraints,
                    # if the student is assigned to the project, otherwise adds 0.
                    #
                    # - `score * (p_id, s_id)`, where
                    #   `(p_id, s_id)` gives a boolean with 0 or 1
                    #
                    #   not assigned: 0|25|50|75|100 * 0 = 0
                    #   assigned:     0|25|50|75|100 * 1 = 0|25|50|75|100
                    #
                    soft_constraints.append(score * self.__model_x[(p_id, s_id)])

                # Variant 2, 3:
                if self.__assignment_variant in [2, 3]:
                    # Collects the students per level of the current project.
                    level = self.__data_per_student[s_id]["level_answer"]
                    p_levels[level].append(self.__model_x[(p_id, s_id)])
                    p_students.append(self.__model_x[(p_id, s_id)])

            # Variant 2, 3:
            if self.__assignment_variant in [2, 3]:
                # Weights the level combinations.
                #
                #  7: ************ 2     ------------ 4
                #  6: ******++++++ 23
                #  5: ++++++++++++ 3
                #  4: ******...... 12    ......------ 14
                #  3: ****++++.... 123
                #  2: ++++++...... 13
                #  1: ............ 1
                #
                #  0: ++++....----       ++++....----
                #  0: ***+++...---       ***+++...---
                #
                # -1: ***??????---

                # Min and max number of students per project.

                min = self.__min_students_per_project
                max = self.__max_students_per_project

                has_max_students = self.__model.new_bool_var("has_max_students")
                self.__model.add(sum(p_students) < max).only_enforce_if(has_max_students.Not())
                self.__model.add(sum(p_students) >= max).only_enforce_if(has_max_students)

                min_max = min + has_max_students

                # Number of projects per student level.

                has_s_level = {
                    # 1: self.__model.new_bool_var("has_students_level_1"),
                    2: self.__model.new_bool_var("has_students_level_2"),
                    3: self.__model.new_bool_var("has_students_level_3"),
                    4: self.__model.new_bool_var("has_students_level_4"),
                }

                for s_level in has_s_level:
                    self.__model.add(sum(p_levels[s_level]) < 1).only_enforce_if(has_s_level[s_level].Not())
                    self.__model.add(sum(p_levels[s_level]) >= 1).only_enforce_if(has_s_level[s_level])
                    used_projects_per_student_level[s_level].append(has_s_level[s_level])

                # Wanted level combinations.

                has_level_2 = self.__model.new_bool_var("has_level_2")
                self.__model.add(sum(p_levels[2]) < min_max).only_enforce_if(has_level_2.Not())
                self.__model.add(sum(p_levels[2]) >= min_max).only_enforce_if(has_level_2)

                has_level_3 = self.__model.new_bool_var("has_level_3")
                self.__model.add(sum(p_levels[3]) < min_max).only_enforce_if(has_level_3.Not())
                self.__model.add(sum(p_levels[3]) >= min_max).only_enforce_if(has_level_3)

                has_level_4 = self.__model.new_bool_var("has_level_4")
                self.__model.add(sum(p_levels[4]) < min_max).only_enforce_if(has_level_4.Not())
                self.__model.add(sum(p_levels[4]) >= min_max).only_enforce_if(has_level_4)

                # Adds the weighted level combinations to the soft constraints.
                #
                # TODO: Results are not good.
                #       - [ ] factor vs score impact

                # NOTE: A higher factor increases the weight of the level over the score.
                #
                # - Projects have a score of 0, 25, 50, 75 or 100 points.
                # - If the level * factor is lower than the score, the score is stronger.
                # - If the level * factor is higher than the score, the level is stronger.
                #
                # factor = 100
                factor = 25
                # factor = 1

                soft_constraints.append(
                    0
                    # The positive combinations.
                    + 1 * factor * has_level_2
                    # FIX: Full level 2 or 4 is not working. Two teams with 14 and 24 instead one 14.
                    + 1 * factor * has_level_4
                    + 1 * factor * has_level_3
                    # The negative combinations.
                    - 1 * factor * sum(used_projects_per_student_level[2])
                    - 1 * factor * sum(used_projects_per_student_level[3])
                    # FIX: Is a higher factor a fix for the level 4 problem (line 360)?
                    - 1 * factor * sum(used_projects_per_student_level[4])
                )

        # Maximizes the soft constraints.
        self.__model.maximize(sum(soft_constraints))

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
        Returns the total score between 0 and 100 for the given project and student.

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

    def __extract_solution(self, solver: cp_model.CpSolver):
        """
        Extracts all successful assignments between projects and students,
        including their scores in the `self.__result` list.

        ```python
        {
            "results": [
                (project_id, student_id, score),
                ...
            ],
            "info": {
                "status_name": str,
                "solution_count": int,
                "wall_time": float,
                "best_objective_bound": float,
                "objective_value": float,
                "total_score": int,
            }
        }
        ```

        Successful assignments are those where the result is `1` (`True`).

        Args:
            solver: The constraint solver.
            result_info: The result info.
        """

        total_score = 0
        self.__results = []
        for p_id in self.__project_ids:
            for s_id in self.__student_ids:
                if solver.Value(self.__model_x[(p_id, s_id)]) == 1:
                    score = self.__get_total_score(p_id, s_id)
                    total_score += score
                    self.__results.append((p_id, s_id, score))

        self.__result_info["total_score"] = total_score

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

        # Checks if the algorithm is already running.
        if AssignmentAlgorithm.__is_running:
            raise AssignmentAlgorithmException("Tried to run the algorithm while it is already running.")

        # Sets the algorithm as running.
        AssignmentAlgorithm.__is_running = True

        # Initializes all possible combinations of project and student.
        self.__init_model_variables()

        # Adds the hard constraints.
        self.__add_hc_one_project_per_student()
        self.__add_hc_students_assigned_equally()
        self.__add_hc_wing_students_assigned_equally()
        self.__add_hc_number_used_projects_equals_number_required()
        self.__add_hc_no_level_24()

        # Adds the soft constraints.
        self.__add_sc_maximize_project_score()

        # Creates the solver.
        solver = cp_model.CpSolver()

        # Sets the time limit for the solver.
        solver.parameters.max_time_in_seconds = self.__max_runtime
        # Sets the relative gap limit for the solver.
        solver.parameters.relative_gap_limit = self.__relative_gap_limit
        # Sets the number of workers for the solver.
        solver.parameters.num_workers = self.__num_workers

        # TODO: Testing different parameters.
        solver.parameters.log_search_progress = False
        # solver.parameters.num_workers = 0
        # solver.parameters.num_workers = 8
        # solver.parameters.num_workers = 16

        # Solves the equation.
        self.__results = []
        self.__has_result = False

        if settings.DEBUG:
            # With the solution printer.
            solution_printer = cp_model.ObjectiveSolutionPrinter()
            status = solver.Solve(self.__model, solution_printer)
        else:
            # Without the solution printer.
            status = solver.Solve(self.__model)

        # Sets the algorithm as not running.
        AssignmentAlgorithm.__is_running = False

        # TODO: Catch the exceptions ...
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # Sets the result info.
            self.__result_info = {
                # "status_name": solver.status_name(),
                # "solution_count": solution_printer.solution_count(),
                # "num_branches": solver.num_branches,
                # "num_booleans": solver.num_booleans,
                # "num_conflicts": solver.num_conflicts,
                # "num_integer_propagations": solution_printer.num_integer_propagations,
                # "wall_time": solver.wall_time,
                # "best_objective_bound": solver.best_objective_bound,
                # "objective_value": solver.objective_value,
                "response_stats": "\n---\n" + solver.response_stats() + "---\n",
                "max_time_in_seconds": solver.parameters.max_time_in_seconds,
                "num_workers": solver.parameters.num_workers,
                "relative_gap_limit": solver.parameters.relative_gap_limit,
                "solution_gap": abs(1 - solver.objective_value / solver.best_objective_bound)
                if solver.best_objective_bound != 0
                else -0,
            }
            # Logs the result info.
            logging.debug(f"OR-Tools: Result info: {self.__result_info}")
            # Extracts the solution.
            self.__extract_solution(solver)
            self.__has_result = True
        else:
            raise AssignmentAlgorithmException(
                "The equation cannot be solved for the given data, or the time has expired."
            )

    def get_result(self) -> dict:  # -> list[tuple[int, int, int]]:
        """
        Returns the assignments as a list of tuples `(project_id, student_id, score)` and
        the solver info if the algorithm has already been executed.

        ```python
        {
            "assignments": [
                (project_id, student_id, score),
                ...
            ],
            "info": {
                "response_stats": str,
                "max_time_in_seconds": int,
                "num_workers": int,
                "relative_gap_limit": float,
                "total_score": int,
            }
        }
        ```

        Raises:
            AssignmentAlgoException: If the result is accessed before the algorithm has been executed.
        """

        if not self.__has_result:
            raise AssignmentAlgorithmException("Tried to access result before it was run.")
        else:
            return {
                "assignments": self.__results,
                "info": self.__result_info,
            }

    def force_run(self):
        """
        Forces the algorithm to run.
        """

        AssignmentAlgorithm.__is_running = False
        self.run()

    @classmethod
    def get_is_running(cls):
        """
        Returns whether the algorithm is running.
        """
        return cls.__is_running


class AssignmentAlgorithmException(Exception):
    """Exception, which is thrown by the *AssignmentAlgo* class."""

    pass
