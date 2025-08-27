import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from team.helper import get_teams_for_view


def generate_teams_pdf():
    """
    Generates a PDF file with the generated teams.

    Returns:
        The PDF file as a buffer.
    """

    # Creates a buffer to store the PDF data.
    buffer = BytesIO()

    # Creates a new canvas.
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)  # The page size.
    margin = 20 * mm  # The page margin in mm.

    # Defines the styles.
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="project_name", fontSize=10))
    styles.add(ParagraphStyle(name="student_name", fontSize=9))
    team_table_style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BOX", (0, 0), (-1, -1), 1, colors.grey),
        ("LINEABOVE", (0, 1), (-1, 1), 1, colors.grey),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgoldenrodyellow),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ])

    # Draws the header.
    title = "Teamzusammenstellung - Software Engineering"
    c.drawCentredString(width / 2, height - margin - 12, title)
    now = datetime.datetime.now()
    timestamp = f"Stand: {now.strftime('%d.%m.%Y %H:%M:%S')}"
    c.setFontSize(8)
    c.drawCentredString(width / 2, height - margin - 25, timestamp)

    # Draws the team tables.
    tables_per_line = 4
    table_gap = 5 * mm  # The gap between tables.
    table_width = (width - 2 * margin - ((tables_per_line - 1) * table_gap)) / tables_per_line  # The table width.
    x_count = 1  # The table count per row.
    y_count = 1  # The table count per column.
    h_max = 0  # The max table height per column.
    x = margin  # The x position of the table.
    y = height - margin - 45  # The y position of the table.

    # Gets the teams.
    teams = get_teams_for_view().get("teams", [])
    for team in teams:
        data = []

        # Adds the team name as first row.
        team_name = f"<b>{team['project_instance'].piid}</b> - {team['project_instance'].project.name}"
        data.append([Paragraph(team_name, styles["project_name"])])

        # Adds the students as next rows.
        for student in team["students"]:
            student_name = student["name"]
            styles["student_name"].textColor = "#000000"
            if student["is_initial_contact"]:
                student_name = f"<b>{student_name}</b> <i>(PL)</i>"
            student_name = f"{student_name} <i>({student['study_program_short']})</i>"
            # if student["is_wing"]:
            #     student_name = f"{student_name} <i>(Wing)</i>"

            if student["is_out"] or not student["is_visible"]:
                student_name = f"<strike>{student_name}</strike>"
                styles["student_name"].textColor = "#dc3545" if student["is_out"] else "#6c757d"
            data.append([Paragraph(student_name, styles["student_name"])])

        # Creates a table.
        t = Table(data, colWidths=[table_width], style=team_table_style)

        # Gets the table size.
        _w, h = t.wrap(0, 0)

        # Saves the max table height for next line of tables.
        h_max = max(h, h_max)

        # Draws the table.
        t.wrapOn(c, width, height)
        t.drawOn(c, x, y - h)

        # Increases the table count per row.
        x_count += 1

        # Sets the next table position.
        x = x + table_width + 5 * mm

        # Checks for new line.
        if x_count > tables_per_line:
            x = margin
            y = y - h_max - table_gap
            x_count = 1
            y_count += 1
            h_max = 0

        # Checks for new page.
        if y_count > 2:
            y = height - margin
            y_count = 1
            c.showPage()  # Closes and starts a new page.

    # Cloases last page.
    c.showPage()

    # Generates the pdf.
    c.save()

    # Moves to the start of the buffer.
    buffer.seek(0)

    return buffer
