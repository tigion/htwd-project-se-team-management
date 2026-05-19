import csv
import io

from app.models import Student
from django.db.models import Avg, F, Count, Prefetch, ProtectedError, Q
from django.db.models.functions import Coalesce
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


def get_peer_feedback_1_results_for_view():
    teams = Team.objects.prefetch_related(
        Prefetch(
            "teammember_set",
            queryset=(
                TeamMember.objects.select_related("student").annotate(
                    # Coalesce(Avg(...), 0.0),
                    feedback_count=Count(
                        "student__received_peer_feedback",
                        filter=Q(student__received_peer_feedback__team_id=F("team_id")),
                    ),
                    avg_contribution=Avg(
                        "student__received_peer_feedback__contribution_score",
                        filter=Q(student__received_peer_feedback__team_id=F("team_id")),
                    ),
                    avg_collaboration=Avg(
                        "student__received_peer_feedback__collaboration_score",
                        filter=Q(student__received_peer_feedback__team_id=F("team_id")),
                    ),
                    avg_reliability=Avg(
                        "student__received_peer_feedback__reliability_score",
                        filter=Q(student__received_peer_feedback__team_id=F("team_id")),
                    ),
                )
            ),
        )
    )

    results = []

    for team in teams:
        member_results = []
        for member in team.teammember_set.all():  # type: ignore
            avg_total = None
            if (
                member.avg_contribution is not None
                and member.avg_collaboration is not None
                and member.avg_reliability is not None
            ):
                avg_total = (member.avg_contribution + member.avg_collaboration + member.avg_reliability) / 3

            member_results.append({
                "student": member.student,
                "student_count": 10,
                "feedback_count": member.feedback_count,
                "avg_contribution": member.avg_contribution,  # or 0.0,
                "avg_collaboration": member.avg_collaboration,
                "avg_reliability": member.avg_reliability,
                "avg_total": avg_total,
            })

        results.append({
            "team": team,
            "members": member_results,
        })

    return results


def get_peer_feedback_1_results_for_view2():
    results = []

    students = {student.pk: student for student in Student.objects.all()}
    teams = Team.objects.all()

    get_peer_feedback_1_results_for_view2()

    for team in teams:
        team_feedbacks = (
            # Team feedbacks grouped by reviewed student, with average scores.
            PeerFeedback1.objects
            .filter(team=team)
            .values("reviewed_student")
            .annotate(
                avg_contribution_score=Avg("contribution_score"),
                avg_collaboration_score=Avg("collaboration_score"),
                avg_reliability_score=Avg("reliability_score"),
            )
        )

        team_results = []
        for feedback in team_feedbacks:
            student = students[feedback["reviewed_student"]]
            avg_contribution_score = feedback["avg_contribution_score"] or 0
            avg_collaboration_score = feedback["avg_collaboration_score"] or 0
            avg_reliability_score = feedback["avg_reliability_score"] or 0

            avg_total_score = (avg_contribution_score + avg_collaboration_score + avg_reliability_score) / 3

            team_results.append({
                "student": student,
                "avg_contribution_score": avg_contribution_score,
                "avg_collaboration_score": avg_collaboration_score,
                "avg_reliability_score": avg_reliability_score,
                "avg_total_score": avg_total_score,
            })

        results.append({
            "team": team,
            "results": team_results,
        })

    return results


def generate_peer_feedback_1_csv():
    # TODO: average score per team and overall

    csv_data = [
        [
            "Projektinstanz",
            "Bewertender Student",
            "Bewerteter Student",
            "Beitrag",
            "Zusammenarbeit",
            "Zuverlässigkeit",
            "Begründung",
        ]
    ]
    feedback_entries = PeerFeedback1.objects.all()
    for feedback in feedback_entries:
        csv_data.append([
            feedback.team.project_instance.piid,
            feedback.reviewing_student.name,
            feedback.reviewed_student.name,
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
