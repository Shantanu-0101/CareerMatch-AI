"""Builds sample resume files (DOCX and PDF) for tests and demos."""
from io import BytesIO

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

SAMPLE_LINES = [
    "Priya Sharma",
    "priya.sharma@example.com | +91 98765 43210 | linkedin.com/in/priya-sharma | github.com/priyasharma",
    "Career Objective",
    "Final-year computer engineering student seeking a Python Developer role.",
    "Education",
    "B.Tech in Computer Engineering, ABC College of Engineering, 2021 - 2025, CGPA 8.4/10",
    "Technical Skills",
    "Python, Flask, SQL, MySQL, HTML, CSS, JavaScript, Git, C, Data Structures",
    "Projects",
    "Career Match AI - Flask, SQLite, Chart.js",
    "Developed a resume analysis web app used by 150+ students in my college.",
    "Built a rule-based scoring engine and improved accuracy of skill detection by 30%.",
    "Library Management System - Python, MySQL",
    "Designed the database schema and implemented book issue and return features.",
    "Experience",
    "Python Intern, XYZ Technologies, Jun 2024 - Aug 2024",
    "Automated weekly reports with Python, which reduced manual work by 5 hours per week.",
    "Collaborated with a team of 4 developers using Git.",
    "Certifications",
    "Python for Data Science - NPTEL (2024)",
    "Achievements",
    "Winner, college hackathon 2024 among 40 teams.",
]


def sample_docx_bytes(lines=SAMPLE_LINES):
    doc = Document()
    for line in lines:
        doc.add_paragraph(line)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def sample_pdf_bytes(lines=SAMPLE_LINES):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in lines:
        c.drawString(40, y, line)
        y -= 18
    c.save()
    return buf.getvalue()
