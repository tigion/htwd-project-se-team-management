"""Im Modul Algo ist der Zuordnungsalgorithmus implementiert, welcher
die Studenten anhand der Antworten aus dem Fragebogen automatisiert
und möglichst optimal einem Projekt und einer Rolle zuweist."""

# from numpy import double
from ortools.sat.python import cp_model as cpm
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
        * Jedes Projekt hat exakt einen Teamleiter.
        * Die Rollen Analyse, Entwurf, Implementierung und Test.
          sind gleichmäßig auf die Teammitglieder verteilt.
    """

    __management_role_id = 0
    """Die ID der Rolle Projektleitung, welche in jedem Team
    einmal vorhandensein muss.

    :type: int"""

    # maximum runtime of ortools solver in seconds
    __max_runtime = 300
    """Zeit in Sekunden, nachdem die Berechnung des Algorithmus abbricht.

    :type: int"""

    # indicates whether the algorithm has already been executed
    __algo_ran = False
    """Indiziert, ob der Algorithmus bereits ausgeführt wurde und ein
    Ergebnis existiert.

    :type: bool"""

    # GAIN FACTORS
    # * they indicate the weight of the corresponding score in the equation.
    # * the higher the gain, the greater the influence of the specific score
    #   on the decision-making process
    # * all gain factors must add up to 1.0
    # weight of the project score
    __project_gain = 0.8
    """Wichtungsfaktor der Projekte bei der Erstellung der Zuordnungen.
    Muss zwischen 0.0 und 1.0 liegen. Je höher der Wert desto höher
    der Einfluss. Bsp.: ``__project_gain = 0.0`` würde bedeuten, dass
    die Rollenwünsche der Studenten gar nicht beachtet werden.
    ``__project_gain`` und ``__role_gain`` müssen in Summe 1 ergeben.

    :type: float
    """
    # weight of the project score
    __role_gain = 0.2
    """Wichtungsfaktor der Rollen bei der Erstellung der Zuordnungen.
    Muss zwischen 0.0 und 1.0 liegen. Je höher der Wert desto höher
    der Einfluss. Bsp.: ``__role_gain = 0.0`` würde bedeuten, dass
    die Rollenwünsche der Studenten gar nicht beachtet werden.
    ``__project_gain`` und ``__role_gain`` müssen in Summe 1 ergeben.

    :type: float
    """

    def __init__(self, project_answers, role_answers, wing_answers, max_scores):
        # init model
        self.__model_vars = {}
        self.__model = cpm.CpModel()

        # set answere data
        self.__project_answers = project_answers
        self.__role_answers = role_answers
        self.__wing_answers = wing_answers

        # set answer scores
        self.__max_project_score = max_scores["project"]
        self.__max_role_score = max_scores["role"]

        # set number of elements
        self.__n_projects = len(project_answers.get(0))
        self.__n_students = len(wing_answers)
        self.__n_roles = len(role_answers.get(0))

        def filter_is_wing(pair):
            return True if pair[1] else False

        self.__n_wings = len(dict(filter(filter_is_wing, self.__wing_answers.items())))

        # set max project slots
        self.__n_project_slots = math.ceil(self.__n_students / self.__n_projects)

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

        self.__init_var_set()
        self.__init_bounds()
        self.__add_hc_one_project_per_student()
        self.__add_hc_students_assigned_equally()
        self.__add_hc_roles_assigned_equally()
        self.__add_sc()

        solver = cpm.CpSolver()
        solver.parameters.max_time_in_seconds = self.__max_runtime
        status = solver.Solve(self.__model)
        if status == cpm.OPTIMAL or status == cpm.FEASIBLE:
            self.__extract_solution(solver)
            self.__algo_ran = True
        else:
            raise AssignmentAlgoException("Equation infeasible for given data")

    def __init_var_set(self):
        """Erstellt ein Dictionary, welches eine ortools-Bool-Variable für
        jede mögliche Kombination aus Projekt, Student und Rolle beinhaltet.

        :return: None
        """

        # p_id ... project
        # s_id ... student
        # r_id ... role of student s_id

        # create dictionary containing ortools-bool variables of every possible assignment
        # the values of the bool vars are set after running the algo/ solving the equation
        # e.g.: vars[(0,2,4)] = True  would mean:
        # student with id 2 is manager of project with id 0
        for p_id in range(self.__n_projects):
            for s_id in range(self.__n_students):
                for r_id in range(self.__n_roles):
                    self.__model_vars[(p_id, s_id, r_id)] = self.__model.NewBoolVar(
                        "(%d,%d,%d)" % (p_id, s_id, r_id)
                    )  # create bool var with name "(p_id,s_id,r_id)"

    def __init_bounds(self):
        # number of students per role lower bound =
        # (lower bound of students per project - manager)//(number of roles - manager)
        self.n_students_per_role_lb = (self.__n_students // self.__n_projects - 1) // (self.__n_roles - 1)
        # number of students per role upper bound =
        # ceil((upper bound of students per project - manager)/(number of roles - manager))
        self.n_students_per_role_ub = math.ceil((self.__n_project_slots - 1) / (self.__n_roles - 1))

        # minimum number of students per project
        self.lb_students_per_project = self.__n_students // self.__n_projects
        # maximum number of students per project
        # e.g.: n_students=3; n_projects=2
        # => lb_students_per_project=1 and hb_students_per_project=2
        if self.__n_students % self.__n_projects == 0:
            self.hb_students_per_project = self.lb_students_per_project
        else:
            self.hb_students_per_project = self.lb_students_per_project + 1

        # minimum number of wing's per project
        self.lb_wings_per_project = self.__n_wings // self.__n_projects
        # maximum number of wing's per project
        if self.__n_wings % self.__n_projects == 0:
            self.hb_wings_per_project = self.lb_wings_per_project
        else:
            self.hb_wings_per_project = self.lb_wings_per_project + 1

    def __add_hc_one_project_per_student(self):
        """Fügt die harte Restriktion "Ein Student ist genau einem
        Projekt zugeteilt" dem model hinzu.

        :return: None
        """
        # add hard constraint "a student is assigned
        # to exactely one project" to model
        for s_id in range(self.__n_students):
            inner_sum = []
            for p_id in range(self.__n_projects):
                for r_id in range(self.__n_roles):
                    inner_sum.append(self.__model_vars[(p_id, s_id, r_id)])
            self.__model.Add(sum(inner_sum) == 1)

    def __add_hc_students_assigned_equally(self):
        """Fügt die harte Restriktion "Studenten sind gleichmäßig auf die
        Projekte aufgeteilt" und "WING-Studenten sind gleichmäßig auf die
        Projekte aufgeteilt" dem model hinzu.

        Bsp.: 30 Studenten, davon 9 WING auf 3 Projekte aufgeteilt, würde
        in folgender Zuordnung resultieren:
        Je 3 WING pro Projekt und insgedamt je 10 Studenten pro Projekt.

        :return: None
        """
        # add hard constraint "students assigned equally" to model
        for p_id in range(self.__n_projects):
            inner_students = []
            inner_wings = []
            for s_id in range(self.__n_students):
                for r_id in range(self.__n_roles):
                    inner_students.append(self.__model_vars[((p_id, s_id, r_id))])
                    if self.__wing_answers[s_id] == 1:
                        inner_wings.append(self.__model_vars[(p_id, s_id, r_id)])
            self.__model.Add(sum(inner_students) >= self.lb_students_per_project)
            self.__model.Add(sum(inner_students) <= self.hb_students_per_project)
            self.__model.Add(sum(inner_wings) >= self.lb_wings_per_project)
            self.__model.Add(sum(inner_wings) <= self.hb_wings_per_project)

    def __add_hc_roles_assigned_equally(self):
        """Fügt die harte Restriktion "Rollen sind gleichmäßig im Team
        aufgeteilt" dem model hinzu.
        Das bedeutet:

            * genau ein Teamleiter pro Team
            * die restlichen Rollen (Analyse, Entwurf, Implementierug,
              Test) sind gleichmäßig verteilt.

        Bsp.: Ein Team, bestehend aus 9 Studenten, würde in folgender Aufteilung
        resultieren: 1x Teamleiter, 2x Analyse, 2x Entwurf,
        2x Implementierung, 2x Test. Geht die Zuteilung bspw. bei 10
        Studenten nicht exakt auf, entscheidet der Algorithmus selbst
        in welche Rolle der 10. Student am besten passt und ordnet ihm
        diese zu.

        :return: Nonenu
        """
        # add hard constraint "roles assigned equally" to model
        for p_id in range(self.__n_projects):
            for r_id in range(self.__n_roles):
                inner_manager = []  # inner sum for r_id == manager
                inner_roles = []  # inner sum for every role except manager
                for s_id in range(self.__n_students):
                    if r_id == self.__management_role_id:  # if role == manager
                        inner_manager.append(self.__model_vars[(p_id, s_id, r_id)])
                    else:  # if role != manager
                        inner_roles.append(self.__model_vars[(p_id, s_id, r_id)])
                if r_id == self.__management_role_id:
                    self.__model.Add(sum(inner_manager) == 1)
                else:
                    self.__model.Add(sum(inner_roles) >= self.n_students_per_role_lb)
                    self.__model.Add(sum(inner_roles) <= self.n_students_per_role_ub)

    def __add_sc(self):
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
        # add soft constraints to model (maximize projectscore and rolescore)
        soft_constraints = []
        for p_id in range(self.__n_projects):
            for s_id in range(self.__n_students):
                for r_id in range(self.__n_roles):
                    score = self.total_score(p_id, s_id, r_id)
                    soft_constraints.append(score * self.__model_vars[(p_id, s_id, r_id)])

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
                for r_id in range(self.__n_roles):
                    if solver.Value(self.__model_vars[(p_id, s_id, r_id)]) == 1:
                        # Also return the score of the result
                        score = self.total_score(p_id, s_id, r_id)
                        self.__result.append((p_id, s_id, r_id, score))

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

    def role_score(self, role, answers):
        """Bewertungsfunktion/ weiche Restriktion für die Rollen.

        :param role: id der Rolle
        :type role: int
        :param answers: beinhaltet die vom Studenten abgegebenen
         Bewertungen zu den Rollen. Aufbau: ``{role_id:score, ....}``
        :type answers: dict{int:int}
        :return: Normalisierter Score zwischen 0-100. Je höher desto besser
         hat der Student die Rolle bewertet.
        :rtype: int"""

        return self.normalize_score(answers.get(role))

    def normalize_score(self, answer_score):
        # shift answer score to start with 0
        # - (1 to max) -> (0 to (max-1))
        score = answer_score - 1
        max_score = self.__max_project_score - 1

        # normalize answer score to between 0 and 100
        # - (0 to (max-1)) -> (0 to 100)
        score = score * 100 / max_score

        return score

    def total_score(self, project, student, role):
        # Weights the normalized project score (project gain .8)
        p_score = self.__project_gain * self.project_score(project, self.__project_answers.get(student))
        # Weights the normalized role score (role gain .2)
        r_score = self.__role_gain * self.role_score(role, self.__role_answers.get(student))
        # Total project and role score between 0 and 100
        score = p_score + r_score

        return score

    def set_project_gain(self, project_gain: float):
        """Setzt den Gain/ die Wichtung für die weiche Restriktion der
        Projektzuteilung.

        :param project_gain: Wichtungswert zwischen 0.0 - 1.0
        :type project_gain: float
        :raises: AssertionError wenn ``type(project_gain) != float``
        :return: None"""
        assert type(project_gain) == float
        self.__project_gain = project_gain

    def get_project_gain(self):
        """
        :return: Gibt den Gain/ die Wichtung für die weiche Restriktion
                 der Projektzuteilung zurück.
        :rtype: float
        """
        return self.__project_gain

    def set_role_gain(self, role_gain: float):
        """Setzt den Gain/ die Wichtung für die weiche Restriktion der
        Rollenzuteilung.

        :param role_gain: Wichtungswert zwischen 0.0 - 1.0
        :type role_gain: float
        :raises: AssertionError wenn ``type(role_gain) != float``
        :return: None"""
        assert type(role_gain) == float
        self.__role_gain = role_gain

    def get_role_gain(self):
        """
        :return: Gibt den Gain/ die Wichtung für die weiche Restriktion
                 der Rollenzuteilung zurück.
        :rtype: float
        """
        return self.__role_gain

    def set_max_runtime(self, max_runtime: int):
        """Setzt die Laufzeitgrenze für den Algorithmus.

        :param max_runtime: Zeit in Sekunden > 0.
        :type max_runtime: int
        :raises: AssertionError wenn type(max_runtime) != int
        :return: None"""
        assert type(max_runtime) == int
        self.__max_runtime = max_runtime

    def get_max_runtime(self):
        """:return: Laufzeitgrenze des Algorithmus in Sekunden
        :rtype: int"""
        return self.__max_runtime

    def get_result(self):
        """Gibt die vollständigen Zuordnungen als List von Tupeln
        zurück, falls der Algorithmus bereits ausgeführt wurde.

        :raises: AssignmentAlgoException wenn auf das Ergebnis vor dem
                 Ausführen des Algorithmus zugegriffen wird.
        :return: Liste von Tupeln als Zuordnung bestehend aus Student,
                 Projekt und Rolle.
        :rtype: list((int,int,int))"""
        if self.__algo_ran == False:
            raise AssignmentAlgoException("tried to access result before running algo")
        else:
            return self.__result