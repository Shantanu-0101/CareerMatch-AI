"""ATS-friendly PDF resumes with ReportLab (single column, real selectable text, standard headings)."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from .resume_builder import SECTION_ORDER

STYLES = {
    "modern": dict(font="Helvetica", bold="Helvetica-Bold", size=10, name_size=22, accent=colors.HexColor("#1e3a8a"),
                   align=TA_LEFT, heading_upper=True, gap=8),
    "classic": dict(font="Times-Roman", bold="Times-Bold", size=11, name_size=20, accent=colors.black,
                    align=TA_CENTER, heading_upper=True, gap=8),
    "compact": dict(font="Helvetica", bold="Helvetica-Bold", size=9, name_size=17, accent=colors.HexColor("#334155"),
                    align=TA_LEFT, heading_upper=False, gap=4),
}

HEADINGS = {"summary": "Professional Summary", "education": "Education", "skills": "Technical Skills",
            "projects": "Projects", "experience": "Work Experience", "certifications": "Certifications",
            "achievements": "Achievements", "languages": "Languages"}


def _e(text):
    return escape(text or "")


def build_pdf(data, template="modern"):
    st = STYLES.get(template, STYLES["modern"])
    buf = BytesIO()
    margin = 14 * mm if template == "compact" else 18 * mm
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=margin,
                            title=f"{data['personal'].get('full_name', 'Resume')} - Resume")

    body = ParagraphStyle("body", fontName=st["font"], fontSize=st["size"], leading=st["size"] * 1.35)
    bold = ParagraphStyle("bold", parent=body, fontName=st["bold"])
    small = ParagraphStyle("small", parent=body, fontSize=st["size"] - 1, textColor=colors.HexColor("#475569"))
    name = ParagraphStyle("name", fontName=st["bold"], fontSize=st["name_size"], leading=st["name_size"] * 1.2,
                          textColor=st["accent"], alignment=st["align"])
    contact = ParagraphStyle("contact", parent=body, alignment=st["align"], textColor=colors.HexColor("#334155"))
    heading = ParagraphStyle("heading", fontName=st["bold"], fontSize=st["size"] + 2, leading=st["size"] * 1.6,
                             textColor=st["accent"], spaceBefore=st["gap"])

    p = data["personal"]
    story = [Paragraph(_e(p.get("full_name")), name), Spacer(1, 3)]
    bits = [p.get(k) for k in ("email", "phone", "location", "linkedin", "github", "website") if p.get(k)]
    if bits:
        story.append(Paragraph(" | ".join(_e(b) for b in bits), contact))

    def section(key):
        title = HEADINGS[key]
        story.append(Paragraph(_e(title.upper() if st["heading_upper"] else title), heading))
        story.append(HRFlowable(width="100%", thickness=0.8, color=st["accent"], spaceAfter=4))

    def bullets(text):
        lines = [l.strip(" -•\t") for l in (text or "").splitlines() if l.strip(" -•\t")]
        if not lines:
            return
        story.append(ListFlowable([ListItem(Paragraph(_e(l), body), leftIndent=10) for l in lines],
                                  bulletType="bullet", start="•", leftIndent=10, bulletFontSize=st["size"] - 2))

    hidden = set(data.get("hidden", []))
    for key in SECTION_ORDER:
        if key in hidden:
            continue
        value = data.get(key)
        if not value:
            continue
        section(key)
        if key == "summary":
            story.append(Paragraph(_e(value), body))
        elif key in ("skills", "languages"):
            story.append(Paragraph(_e(value), body))
        elif key == "education":
            for ed in value:
                story.append(Paragraph(f"<b>{_e(ed['degree'])}</b>" + (f", {_e(ed['institution'])}" if ed["institution"] else ""), body))
                meta = " | ".join(x for x in (ed["year"], ed["score"]) if x)
                if meta:
                    story.append(Paragraph(_e(meta), small))
                story.append(Spacer(1, 3))
        elif key == "projects":
            for pr in value:
                line = f"<b>{_e(pr['title'])}</b>"
                if pr["tech"]:
                    line += f" | <i>{_e(pr['tech'])}</i>"
                story.append(Paragraph(line, body))
                if pr["link"]:
                    story.append(Paragraph(_e(pr["link"]), small))
                bullets(pr["description"])
                story.append(Spacer(1, 3))
        elif key == "experience":
            for ex in value:
                story.append(Paragraph(f"<b>{_e(ex['role'])}</b>" + (f", {_e(ex['company'])}" if ex["company"] else ""), body))
                if ex["duration"]:
                    story.append(Paragraph(_e(ex["duration"]), small))
                bullets(ex["description"])
                story.append(Spacer(1, 3))
        elif key == "certifications":
            for c in value:
                meta = ", ".join(x for x in (c["issuer"], c["year"]) if x)
                story.append(Paragraph(f"<b>{_e(c['name'])}</b>" + (f" - {_e(meta)}" if meta else ""), body))
        elif key == "achievements":
            bullets("\n".join(a["text"] for a in value))

    doc.build(story)
    return buf.getvalue()
