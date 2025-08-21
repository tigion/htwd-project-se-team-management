"""
This module implements the assignment algorithm that assigns students
to projects as optimally as possible based on their survey responses.
"""

from ortools.sat.python import cp_model

import math


class AssignmentAlgoException(Exception):
    """Exception, welche von der Klasse *AssignmentAlgo*
    geworfen wird."""

    pass


class AssignmentAlgo:
    """Der Zuordnungsalgorithmus wurde mithilfe des CP-SAT Solver
    von Google ortools umgesetzt. Dies ist ein sogenannter Constraint
    Solver, welchen man gewisse Regeln in Form von harten Restriktionen
    und weichen Restriktionen übergibt. Mit den Restriktionen und den
    eingegebenen Daten berechnet dieser automatisch das beste Ergebnis.
    Wenn der Algorithmus gestartet wird, werden automatisch der Hardware
    entsprechend mehrere Threads zum schnelleren Lösen des Problems
    erzeugt. Das Threadhandling und die Speicherverwaltung wird
    automatisch von ortools geregelt. Weitere Information zu ortools
    sind hier zu finden:
    https://developers.google.com/optimization/

    Harte Restriktionen sind Bedingungen, die unter allen Umständen
    eingehalten werden müssen. Gibt es ein Ergebnis, welches nicht alle
    harten Restriktionen erfüllt, so ist das Ergebnis ungültig. Ein
    Beispiel für ein harte Restriktion ist z.B. "Jeder Student muss exakt
    einem Projekt zugeordnet sein".
    Die harten Restriktion sind in den ``add_hc*`` Funktionen implementiert.
    Diese Restriktionen müssen zu einer mathematischen Summenformel
    umformuliert werden. Wie das im Detail funktionert ist in diesem Artikel
    anschaulich beschrieben:
    https://towardsdatascience.com/where-you-should-drop-deep-learning-in-favor-of-constraint-solvers-eaab9f11ef45

    Weiche Restriktionen hingegen sind meist Bewertungsfunktionen, welche
    die Güte einer potenziellen Lösung bewerten. Dem Algorithmus können
    diese Bewertungsfunktionen/weichen Restriktionen übergeben werden.
    Dabei kann bestimmt werden, ob der Wert der entsprechenden Funktion minimiert
    oder maximiert werden soll. Ein Beispiel für eine weiche Restriktion
    ist die Zuteilung eines Studenten in Zusammenhang mit seinem Projektwunsch
    aus dem Fragebogen. Wenn ein Student einem Projekt zugeteilt wird,
    welches er sich auch im Fragebogen gewünscht hat, könnte die Funktion
    bspw. ein Score von 100 zurückgeben. Gelangt er in ein Projekt, in das
    der Student auf keinen Fall wollte, könnte sie ein Score von 0
    zurückgeben.
    Die weichen Restriktionen sind in der ``add_sc()`` Funktion implementiert.

    Folgende harte Restriktionen sind implementiert:

        * Jeder Student ist exakt einem Projekt zugeteilt.
        * Studenten sind gleichmäßig auf die Teams verteilt.
        * WING-Studenten sind gleichmäßig auf die Teams verteilt.


    Sources:
    - https://medium.com/data-science/where-you-should-drop-deep-learning-in-favor-of-constraint-solvers-eaab9f11ef45
    """

    __max_runtime = 300
    """Time in seconds after which the calculation of the algorithm aborts."""

    __algo_ran = False
    """Indicates whether the algorithm has already been executed and a result exists."""

    # GAIN FACTORS
    # * they indicate the weight of the corresponding score in the equation.
    # * the higher the gain, the greater the influence of the specific score
    #   on the decision-making process
    # * all gain factors must add up to 1.0

    # weight of the project score
    __project_gain = 1.0
    # __project_gain = 0.8
    """Wichtungsfaktor der Projekte bei der Erstellung der Zuordnungen.
    Muss zwischen 0.0 und 1.0 liegen. Je höher der Wert desto höher
    der Einfluss. Bsp.: ``__project_gain = 0.0`` würde bedeuten, dass
    die Rollenwünsche der Studenten gar nicht beachtet werden.
    ``__project_gain`` und ``__role_gain`` müssen in Summe 1 ergeben.

    :type: float
    """

    def __init__(self, project_answers, wing_answers, max_scores, min_project_slots):
        # Initializes the model.
        self.__model_vars = {}
        self.__model = cp_model.CpModel()

        # Sets the answer data.
        self.__project_answers = project_answers
        self.__wing_answers = wing_answers

        # Sets the max project scores.
        self.__max_project_score = max_scores["project"]

        # Sets the number of projects and students.
        self.__n_projects = len(project_answers.get(0))
        self.__n_students = len(wing_answers)

        def filter_is_wing(pair):
            """Filter function for students which are wings."""
            return True if pair[1] else False

        # Sets the number of wings.
        self.__n_wing_students = len(dict(filter(filter_is_wing, self.__wing_answers.items())))

        # Sets the number of min project slots.
        self.__n_min_project_slots = min_project_slots

        # Sets the number of projects required.
        self.__n_projects_required = math.floor(self.__n_students / self.__n_min_project_slots)

    def run(self):
        """Startet den Algorithmus. Die Funktion blockiert solange, bis
        die Berechnung abgeschlossen oder abgebrochen ist. Nach beendeter
        Berechnung wird das Ergebnis automatisch mit der ``extract_solution()``
        Funktion ausgelesen.

        Die Berechnung wird beendet, wenn
            * ein optimales Ergebnis gefunden wurde,
            * die übergebene Aufgabe/ Funktion nicht lösbar ist oder
            * die max_runtime überschritten wurde. In diesem Fall wird die
              bis dahin beste Lösung, die gefunden wurde, verwendet.

        :raises: AssignmentAlgoException wenn die Gleichung, die dem Solver
            übergeben wurde, nicht lösbar ist oder kein Ergebnis in der
            vorgegebenen Zeit gefunden wurde.
        :return: None
        """

        # Initializes all possible combinations of project and student.
        self.__init_var_set()

        # Initializes the limits for students and wing students per project.
        self.__init_limits()

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
        status = solver.Solve(self.__model)
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            self.__extract_solution(solver)
            self.__algo_ran = True
        else:
            raise AssignmentAlgoException("The equation cannot be solved for the given data, or the time has expired.")

    def __init_var_set(self):
        """
        Creates a dictionary which contains OR-Tools bool 0-1 variables for
        every possible combination of project and student.

        The value of a bool 0-1 variable, for example `[(4,2)]`, means the following:
        - `0` (`False`) ... The student with id `2` is not in project with id `4`.
        - `1` (`True`) ... The student with id `2` is in project with id `4`.
        """

        for p_id in range(self.__n_projects):
            for s_id in range(self.__n_students):
                self.__model_vars[(p_id, s_id)] = self.__model.NewBoolVar("(%d, %d)" % (p_id, s_id))

    def __init_limits(self):
        """
        Sets the limits (bounds) for the number of students per project and the
        number of wing students per project.
        """

        # Sets the minimum number of students per project.
        self.min_students_per_project = self.__n_min_project_slots

        # Sets the maximum number of students per project.
        self.max_students_per_project = self.min_students_per_project
        if self.__n_students % self.min_students_per_project != 0:
            self.max_students_per_project += 1

        # Sets the minimum number of wings per project.
        self.min_wings_per_project = math.floor(self.__n_wing_students / self.__n_projects_required)

        # Sets the maximum number of wings per project.
        self.max_wings_per_project = self.min_wings_per_project
        if self.__n_wing_students % self.__n_projects_required != 0:
            self.max_wings_per_project = self.min_wings_per_project + 1

    def __add_hc_one_project_per_student(self):
        """
        Adds the following hard constraints to the model:
        - A student is assigned to exactly one project.
        """

        for s_id in range(self.__n_students):
            student_projects = []
            for p_id in range(self.__n_projects):
                student_projects.append(self.__model_vars[(p_id, s_id)])
            self.__model.Add(sum(student_projects) == 1)

    def __add_hc_students_assigned_equally(self):
        """
        Adds the following hard constraints to the model:
        - Students are assigned equally to projects.
        - Number of students per project should be 0 or between min and max.
        """

        for p_id in range(self.__n_projects):
            project_students = []
            for s_id in range(self.__n_students):
                project_students.append(self.__model_vars[(p_id, s_id)])

            # Number of students should be 0 or between min and max.
            b = self.__model.NewBoolVar("b")
            self.__model.Add(sum(project_students) == 0).OnlyEnforceIf(b.Not())
            self.__model.Add(sum(project_students) >= self.min_students_per_project).OnlyEnforceIf(b)
            self.__model.Add(sum(project_students) <= self.max_students_per_project).OnlyEnforceIf(b)

    def __add_hc_wing_students_assigned_equally(self):
        """
        Adds the following hard constraints to the model:
        - Wing students are assigned equally to projects.
        """

        for p_id in range(self.__n_projects):
            project_wing_students = []
            for s_id in range(self.__n_students):
                if self.__wing_answers[s_id] == 1:
                    project_wing_students.append(self.__model_vars[(p_id, s_id)])

            # Number of wings should be between min and max.
            self.__model.Add(sum(project_wing_students) >= self.min_wings_per_project)
            self.__model.Add(sum(project_wing_students) <= self.max_wings_per_project)

    def __add_hc_number_used_projects_equals_number_required(self):
        """
        Adds the following hard constraints to the model:
        - Number of used projects should be the number of required projects.
        """

        used_projects_count = 0
        for p_id in range(self.__n_projects):
            project_students = []
            for s_id in range(self.__n_students):
                project_students.append(self.__model_vars[(p_id, s_id)])
            has_students = self.__model.NewBoolVar("has_students")
            self.__model.Add(sum(project_students) == 0).OnlyEnforceIf(has_students.Not())
            self.__model.Add(sum(project_students) > 0).OnlyEnforceIf(has_students)
            used_projects_count += has_students

        self.__model.Add(used_projects_count == self.__n_projects_required)

    def __add_sc_maximize_project_score(self):
        """Fügt dem model die weichen Restriktionen hinzu. Diese
        Restriktionen sind implementiert:

            * zugeteiltes Projekt verglichen mit der Bewertung, die
              der Student dazu abgegeben hat. Dies wird mit einem Score
              zwischen 0 und 100 von der ``project_score()`` Funktion bewertet.
            * zugeteilte Rolle verglichen mit der Bewertung, die der
              Student dazu abgegeben hat. Dies wird mit einem Score
              zwischen 0 und 100 von der ``role_score()`` Funktion bewertet.

        Der project_score und der role_score werden mit ihren entsprechenden
        Gain Faktoren multipliziert und anschließend in der Variablen score
        summiert. Dieser Wert bestimmt wie gut eine spezifische Zuordnung
        ist. Je höher der Wert desto besser passt die Zuordnung auf die
        Wünsche des jeweiligen Studenten. Mittels
        ``self.__model.Maximize(sum(soft_constraints))`` wird der Solver
        diesen Wert versuchen zu maximieren

        :return: None
        """
        # add soft constraints to model (maximize projectscore)
        soft_constraints = []
        for p_id in range(self.__n_projects):
            for s_id in range(self.__n_students):
                score = self.total_score(p_id, s_id)
                soft_constraints.append(score * self.__model_vars[(p_id, s_id)])

        self.__model.Maximize(sum(soft_constraints))

    def __extract_solution(self, solver):
        """Iteriert über alle Variablen im dict self.__model_vars und prüft,
        ob sie == 1 also wahr und somit in der Lösungsmenge enthalten
        sind. Wenn dies der Fall ist, wird eine enstsprechende Zuordnung
        bestehend aus ProjektID, StudentID und RollenID erzeugt und
        ``self.__result`` hinzugefügt.

        :param solver: Contstraint Solver
        :type solver: ortools.sat.python.cp_model.CpSolver
        :return: None
        """

        self.__result = []
        for p_id in range(self.__n_projects):
            for s_id in range(self.__n_students):
                if solver.Value(self.__model_vars[(p_id, s_id)]) == 1:
                    # Also return the score of the result
                    score = self.total_score(p_id, s_id)
                    self.__result.append((p_id, s_id, score))

    def project_score(self, project, answers):
        """Bewertungsfunktion/ weiche Restriktion für die Projekte.

        :param project: id des Projektes
        :type project: int
        :param answers: beinhaltet die vom Studenten abgegebenen
         Bewertungen zu den Projekten. Aufbau: ``{project_id:score, ....}``
        :type answers: dict{int:int}
        :return: Normalisierter Score zwischen 0-100. Je höher desto besser
         hat der Student das Projekt bewertet.
        :rtype: int"""

        return self.normalize_score(answers.get(project))

    def normalize_score(self, answer_score):
        # shift answer score to start with 0
        # - (1 to max) -> (0 to (max-1))
        score = answer_score - 1
        max_score = self.__max_project_score - 1

        # normalize answer score to between 0 and 100
        # - (0 to (max-1)) -> (0 to 100)
        score = score * 100 / max_score

        return score

    def total_score(self, project, student):
        # Weights the normalized project score (project gain .8)
        p_score = self.__project_gain * self.project_score(project, self.__project_answers.get(student))
        # Total project and role score between 0 and 100
        # score = p_score + r_score
        score = p_score

        return score

    def set_max_runtime(self, max_runtime: int):
        # TODO: Not used yet. Later, the max runtime should be set by the user.
        assert type(max_runtime) is int
        self.__max_runtime = max_runtime

    def get_max_runtime(self):
        # TODO: Not used yet. Later, the max runtime should be set by the user.
        return self.__max_runtime

    def get_result(self):
        """Gibt die vollständigen Zuordnungen als List von Tupeln
        zurück, falls der Algorithmus bereits ausgeführt wurde.

        :raises: AssignmentAlgoException wenn auf das Ergebnis vor dem
                 Ausführen des Algorithmus zugegriffen wird.
        :return: Liste von Tupeln als Zuordnung bestehend aus Student,
                 Projekt und Rolle.
        :rtype: list((int,int))"""
        if not self.__algo_ran:
            raise AssignmentAlgoException("tried to access result before running algo")
        else:
            return self.__result
