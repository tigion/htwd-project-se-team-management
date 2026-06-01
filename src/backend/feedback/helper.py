import csv
import io
import math

from django.db.models import Avg, Count, F, Prefetch, ProtectedError, Q
from django.utils.html import format_html
from team.models import Team, TeamMember

from .models import FEEDBACK_SCORES, PeerFeedback1


def load_peer_feedback_1_data_for_form(student):
    """
    Returns the peer feedback 1 data for the given student.

    If the student has no given feedback, the default scores are used.
    """

    default_score = FEEDBACK_SCORES["default"]

    # All team members assigned to the same team as the student, excluding the student itself.
    assigned_team_members = (
        TeamMember.objects
        .filter(team__teammember__student=student)
        .exclude(student=student)
        .select_related("student")
        .distinct()
    )

    # All peer feedbacks given by the student for the assigned team members.
    peer_feedbacks = PeerFeedback1.objects.filter(
        reviewing_student=student,
        reviewed_student__in=[team_member.student for team_member in assigned_team_members],
    )

    # Maps the reviewed student's ID to the corresponding peer feedback given by the student.
    feedback_map = {feedback.reviewed_student.pk: feedback for feedback in peer_feedbacks}

    # Fills the feedback data for the form.
    feedback_data = []
    for team_member in assigned_team_members:
        peer_feedback = feedback_map.get(team_member.student.pk)

        feedback_data.append({
            "id": team_member.pk,
            "student": team_member.student,
            "has_peer_feedback": peer_feedback is not None,
            "peer_feedback": {
                "contribution_score": (peer_feedback.contribution_score if peer_feedback else default_score),
                "collaboration_score": (peer_feedback.collaboration_score if peer_feedback else default_score),
                "reliability_score": (peer_feedback.reliability_score if peer_feedback else default_score),
                "reason": (format_html("{}", peer_feedback.reason) if peer_feedback else ""),
            },
        })

    return feedback_data


def get_peer_feedback_1_statistics_for_view():
    """
    Returns the peer feedback 1 statistics for the view.
    """

    stats = {
        "total_feedback": {
            "total_count": 0,
            "filled_count": 0,
            "filled_percent": 0,
            "empty_count": 0,
        },
        "feedbacks_per_team": [],
    }

    total_possible_feedback_count = 0
    feedback_stats = []

    teams = Team.objects.all()
    for team in teams:
        member_count = TeamMember.objects.filter(team=team).count()
        possible_feedback_count = member_count * (member_count - 1)
        total_possible_feedback_count += possible_feedback_count

        filled_feedback_count = PeerFeedback1.objects.filter(team=team).count()
        feedback_stats.append({
            "team_id": team.project_instance.piid,
            "team_member_count": member_count,
            "feedback": {
                "total_count": possible_feedback_count,
                "filled_count": filled_feedback_count,
                "filled_percent": (filled_feedback_count / possible_feedback_count * 100)
                if possible_feedback_count > 0
                else 0,
                "empty_count": possible_feedback_count - filled_feedback_count,
            },
        })

    total_filled_feedback_count = PeerFeedback1.objects.count()
    total_filled_feedback_percent = (
        total_filled_feedback_count / total_possible_feedback_count * 100 if total_possible_feedback_count > 0 else 0
    )

    stats["total_feedback"]["total_count"] = total_possible_feedback_count
    stats["total_feedback"]["filled_count"] = total_filled_feedback_count
    stats["total_feedback"]["filled_percent"] = total_filled_feedback_percent
    stats["total_feedback"]["empty_count"] = total_possible_feedback_count - total_filled_feedback_count
    stats["feedbacks_per_team"] = feedback_stats

    return stats


def get_peer_feedback_average_scores_by_team(number=1):
    """
    Returns the teams with their average peer feedback 1 scores and count.

    Args:
        number (int): The number 1 (default) or 2 of the peer feedback to use.
    """

    if number not in (1, 2):
        raise ValueError("Invalid peer feedback number. Must be 1 or 2.")

    feedback_relation = f"student__received_peer_feedback_{number}"
    team_filter = Q(**{f"{feedback_relation}__team_id": F("team_id")})

    teams = Team.objects.prefetch_related(
        Prefetch(
            "teammember_set",
            queryset=(
                TeamMember.objects
                .select_related("student")
                .annotate(
                    # x = Coalesce(Avg(...), 0.0),
                    feedback_count=Count(
                        feedback_relation,
                        filter=team_filter,
                    ),
                    avg_contribution=Avg(
                        f"{feedback_relation}__contribution_score",
                        filter=team_filter,
                    ),
                    avg_collaboration=Avg(
                        f"{feedback_relation}__collaboration_score",
                        filter=team_filter,
                    ),
                    avg_reliability=Avg(
                        f"{feedback_relation}__reliability_score",
                        filter=team_filter,
                    ),
                )
                .order_by("student__last_name")
            ),
        )
    )

    return teams


def get_peer_feedback_reasons_by_team_member(number=1):
    """
    Returns peer feedback reasons grouped by (project_instance_id, student_id).

    Args:
        number (int): The number 1 (default) or 2 of the peer feedback to use.
    """

    if number not in (1, 2):
        raise ValueError("Invalid feedback number. Must be 1 or 2.")

    relation = f"student__received_peer_feedback_{number}"

    team_members = TeamMember.objects.prefetch_related(
        Prefetch(
            relation,
            to_attr="peer_feedbacks",
        )
    )

    reasons_by_student = {}
    for team_member in team_members:
        key = (team_member.team.project_instance.piid, team_member.student.pk)
        reasons = [feedback.reason for feedback in team_member.student.peer_feedbacks]
        reasons_by_student[key] = reasons

    return reasons_by_student


def score_to_percentage(score, score_min, score_max, percent_min, percent_max, round_digits=None):
    """
    Converts a score to a percentage value.

    Args:
        score (float): The score to convert.
        score_min (float): The minimum possible score.
        score_max (float): The maximum possible score.
        percent_min (float): The minimum percentage value corresponding to the minimum score.
        percent_max (float): The maximum percentage value corresponding to the maximum score.
        round_digits (int, optional): The number of decimal places to round the percentage to. If None, no rounding is applied.
    """

    percent = percent_min + (score - score_min) * (percent_max - percent_min) / (score_max - score_min)

    if round_digits is not None:
        percent = round(percent, round_digits)

    return percent


def calculate_peer_feedback_summary(avg_contribution, avg_collaboration, avg_reliability):
    """
    Returns the average total score and percentage for the given values.

    Args:
        avg_contribution (float): The average contribution score.
        avg_collaboration (float): The average collaboration score.
        avg_reliability (float): The average reliability score.
    """

    score_min = FEEDBACK_SCORES["min"]
    score_max = FEEDBACK_SCORES["max"]
    percent_min = FEEDBACK_SCORES["percent_min"]
    percent_max = FEEDBACK_SCORES["percent_max"]

    avg_total = None
    avg_total_percent = None
    avg_total_percent_str = ""

    if avg_contribution is not None and avg_collaboration is not None and avg_reliability is not None:
        avg_total = (avg_contribution + avg_collaboration + avg_reliability) / 3
        avg_total_percent = score_to_percentage(avg_total, score_min, score_max, percent_min, percent_max, 1)
        avg_total_percent_str = f"{avg_total_percent}%"

    choice = FEEDBACK_SCORES["choices"].get(round(avg_total), {}) if avg_total is not None else {}

    return {
        "avg_total": avg_total,
        "avg_total_percent": avg_total_percent,
        "avg_total_percent_str": avg_total_percent_str,
        "avg_total_color": choice.get("color", "gray") if avg_total is not None else "gray",
        "avg_total_icon": choice.get("icon", "bi-record") if avg_total is not None else "bi-record",
    }


def get_peer_feedback_1_results_for_view():
    """
    Returns the peer feedback 1 results for the view.
    """

    teams = get_peer_feedback_average_scores_by_team()
    reasons_map = get_peer_feedback_reasons_by_team_member()

    results = []

    for team in teams:
        member_results = []
        members = team.teammember_set.all()  # type: ignore
        possible_feedback_count = members.count() - 1
        for member in members:
            peer_feedback_summary = calculate_peer_feedback_summary(
                member.avg_contribution, member.avg_collaboration, member.avg_reliability
            )

            possible_feedback_color = "text-bg-danger"
            if member.feedback_count == possible_feedback_count:
                possible_feedback_color = "text-bg-success"
            elif member.feedback_count >= math.ceil(possible_feedback_count / 2):
                possible_feedback_color = "text-bg-warning"

            member_results.append({
                "student": member.student,
                "feedback_count": member.feedback_count,
                "possible_feedback_color": possible_feedback_color,
                "avg_contribution": member.avg_contribution,
                "avg_collaboration": member.avg_collaboration,
                "avg_reliability": member.avg_reliability,
                "avg_total": peer_feedback_summary["avg_total"],
                "avg_total_percent_str": peer_feedback_summary["avg_total_percent_str"],
                "avg_total_color": peer_feedback_summary["avg_total_color"],
                "avg_total_icon": peer_feedback_summary["avg_total_icon"],
                "reasons": reasons_map.get((team.project_instance.piid, member.student.pk), []),
            })

        results.append({
            "team": team,
            "members": member_results,
            "possible_feedback_count": possible_feedback_count,
        })

    return results


def generate_peer_feedback_1_avg_csv():
    """
    Generates the CSV file content with the average peer feedback 1 scores and reasons.
    """

    teams = get_peer_feedback_average_scores_by_team()
    reasons_map = get_peer_feedback_reasons_by_team_member()

    csv_data = [
        [
            "Team",
            "Bewerteter Student",
            "ø Beitrag",
            "ø Zusammenarbeit",
            "ø Zuverlässigkeit",
            "ø Gesamt",
            f"% Bewertung ({FEEDBACK_SCORES['percent_min']} bis {FEEDBACK_SCORES['percent_max']}%)",
            "Begründungen",
        ]
    ]

    for team in teams:
        members = team.teammember_set.all()  # type: ignore
        for member in members:
            reasons = reasons_map.get((team.project_instance.piid, member.student.pk), [])
            average_total_values = calculate_peer_feedback_summary(
                member.avg_contribution, member.avg_collaboration, member.avg_reliability
            )
            csv_data.append([
                team.project_instance.piid,
                member.student.name,
                member.avg_contribution,
                member.avg_collaboration,
                member.avg_reliability,
                average_total_values["avg_total"],
                average_total_values["avg_total_percent"],
                "\r\n---\r\n".join(reasons),
            ])

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=",")
    writer.writerows(csv_data)

    # StringIO -> BytesIO
    bytes_buffer = io.BytesIO()
    bytes_buffer.write(buffer.getvalue().encode("utf-8-sig"))
    bytes_buffer.seek(0)

    return bytes_buffer


def generate_peer_feedback_1_csv():
    """
    Generates the CSV file content with the peer feedback 1 data.
    """

    csv_data = [
        [
            "Team",
            "Bewerteter Student",
            "Bewertender Student",
            "Beitrag",
            "Zusammenarbeit",
            "Zuverlässigkeit",
            "Begründung",
        ]
    ]
    feedback_entries = PeerFeedback1.objects.all().order_by(
        "team__project_instance__project__pid",
        "team__project_instance__number",
        "reviewed_student__last_name",
        "reviewed_student__first_name",
        "reviewing_student__last_name",
        "reviewing_student__first_name",
    )
    for feedback in feedback_entries:
        csv_data.append([
            feedback.team.project_instance.piid,
            feedback.reviewed_student.name,
            feedback.reviewing_student.name,
            feedback.contribution_score,
            feedback.collaboration_score,
            feedback.reliability_score,
            feedback.reason,
        ])

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=",")
    writer.writerows(csv_data)

    # StringIO -> BytesIO
    bytes_buffer = io.BytesIO()
    bytes_buffer.write(buffer.getvalue().encode("utf-8-sig"))
    bytes_buffer.seek(0)

    return bytes_buffer


def delete_feedback_data_for_student(student_id: int):
    """
    Deletes the feedback data for the given student.

    Args:
        student_id (int): The ID of the student.
    """

    try:
        PeerFeedback1.objects.filter(reviewing_student__id=student_id).delete()
        PeerFeedback1.objects.filter(reviewed_student__id=student_id).delete()
    except ProtectedError as e:
        print(f"Error deleting feedback data for student ID {student_id}: {e}")


def delete_feedback_data():
    """
    Deletes all feedback data.
    """

    try:
        PeerFeedback1.objects.all().delete()
    except ProtectedError as e:
        print(f"Error deleting all feedback data: {e}")
