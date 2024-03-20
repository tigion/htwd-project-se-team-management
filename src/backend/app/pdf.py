from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from team.helper import get_prepared_teams_for_view


def generate_teams_pdf():
    # create buffer
    buffer = BytesIO()

    # create canvas
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)  # page size
    margin = 20 * mm  # page margin in mm

    # define styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="project_name", fontSize=8))
    styles.add(ParagraphStyle(name="student_name", fontSize=9))
    team_table_style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgoldenrodyellow),
    ])

    # create and draw header
    title = "Teams"
    c.drawCentredString(width / 2, height - margin - 12, title)

    # create and draw team tables
    tables_per_line = 4
    table_gap = 5 * mm  # gap between tables
    table_width = (width - 2 * margin - ((tables_per_line - 1) * table_gap)) / tables_per_line
    x_count = 1  # table count per row
    y_count = 1  # table count per column
    h_max = 0  # max table height per column
    x = margin  # x position of the table
    y = height - margin - 32  # y position of the table

    # get teams
    teams = get_prepared_teams_for_view()
    for team in teams:
        # create new empty table data
        data = []

        # add team name as first row
        team_name = f"<b>{team['project'].pid}</b>: {team['project'].name}"
        data.append([Paragraph(team_name, styles["project_name"])])

        # add students as next rows
        for student in team["students"]:
            student_name = student["name"]
            styles["student_name"].textColor = "#000000"
            if student["is_project_leader"]:
                student_name = f"<b>{student_name}</b> <i>(PL)</i>"
            if student["is_wing"]:
                student_name = f"{student_name} <i>(Wing)</i>"
            if student["is_out"] or not student["is_visible"]:
                student_name = f"<strike>{student_name}</strike>"
                styles["student_name"].textColor = "#dc3545" if student["is_out"] else "#6c757d"
            data.append([Paragraph(student_name, styles["student_name"])])

        # create table
        t = Table(data, colWidths=[table_width], style=team_table_style)

        # get table size
        w, h = t.wrap(0, 0)

        # save max table height for next line of tables
        h_max = max(h, h_max)

        # draw table
        t.wrapOn(c, width, height)
        t.drawOn(c, x, y - h)

        # increase table count per row
        x_count += 1

        # set next table position
        x = x + table_width + 5 * mm

        # check for new line
        if x_count > tables_per_line:
            x = margin
            y = y - h_max - table_gap
            x_count = 1
            y_count += 1
            h_max = 0

        # check for new page
        if y_count > 2:
            y = height - margin
            y_count = 1
            c.showPage()  # add new page

    # last page
    c.showPage()

    # generate pdf
    c.save()

    # move to the beginning
    buffer.seek(0)

    return buffer
