"""Transparent, rule-based resume scoring (always used for the score) + optional AI feedback.

RUBRIC (100 points)
  1. Technical skills ........... 20   2 points per detected technical skill (max 10 skills)
  2. Role keyword relevance ..... 10   share of the target-role skills found in the resume
  3. Education .................. 10   section 4, degree named 3, marks/CGPA given 3
  4. Projects ................... 15   section 5, enough detail 5, technologies named 5
  5. Experience ................. 15   experience/internship section 7, action verbs 8
  6. Achievements & impact ...... 10   measurable results 6, certifications/achievements section 4
  7. Formatting & structure ..... 20   email 4, phone 3, LinkedIn/GitHub 3, length 5, sections 5
"""
import re

from ..data.skills import SECTION_LABELS, requirements_for
from .ai_service import AIError, get_ai
from .resume_parser import detect_skills, personal_info, split_sections

SOFT_SKILLS = {"Communication", "Problem Solving", "Teamwork", "Leadership"}

ACTION_VERBS = ["developed", "built", "designed", "implemented", "created", "led", "managed", "improved",
                "optimized", "optimised", "automated", "deployed", "analyzed", "analysed", "collaborated",
                "reduced", "increased", "achieved", "launched", "engineered", "integrated", "tested",
                "organized", "organised", "coordinated", "trained", "delivered", "maintained"]

DEGREE_RE = re.compile(r"\b(b\.?\s?tech|b\.?e\.?|b\.?sc|bca|mca|m\.?\s?tech|mba|m\.?sc|bachelor|master|diploma|"
                       r"ph\.?d|hsc|ssc|12th|10th|b\.?com)\b", re.IGNORECASE)
MARKS_RE = re.compile(r"(cgpa|sgpa|gpa|percentage|\b\d{2}(\.\d+)?\s?%|\b\d\.\d{1,2}\s?/\s?10)", re.IGNORECASE)
METRIC_RE = re.compile(r"(\b\d+(\.\d+)?\s?%|\b\d+\+|\b\d+x\b|\b\d{2,}\s?(users|students|clients|customers|downloads|"
                       r"members|participants|requests|records|teams|hours|projects))", re.IGNORECASE)


def _check(label, points, max_points, tip):
    points = round(max(0, min(points, max_points)), 1)
    return {"label": label, "points": points, "max": max_points, "passed": points >= max_points, "tip": tip}


def _category(key, name, checks):
    score = round(sum(c["points"] for c in checks), 1)
    maximum = sum(c["max"] for c in checks)
    return {"key": key, "name": name, "score": score, "max": maximum,
            "percent": round(100 * score / maximum) if maximum else 0, "checks": checks}


def score_resume(text, role, company=""):
    sections = split_sections(text)
    present = [k for k in SECTION_LABELS if sections.get(k, "").strip() or k in sections]
    skills = detect_skills(text)
    tech_skills = [s for s in skills if s not in SOFT_SKILLS]
    info = personal_info(text, sections)
    words = len(text.split())
    required = requirements_for(role, company)
    lower_skills = {s.lower() for s in skills}
    matched = [s for s in required if s.lower() in lower_skills]
    missing = [s for s in required if s.lower() not in lower_skills]

    cats = []
    # 1. Technical skills
    cats.append(_category("skills", "Technical Skills", [
        _check(f"{len(tech_skills)} technical skill(s) detected (2 pts each, up to 10)", 2 * min(len(tech_skills), 10), 20,
               "List more of the technical skills you actually know in a clear 'Technical Skills' section."),
    ]))
    # 2. Keyword relevance
    rel = 10 * len(matched) / len(required) if required else 0
    cats.append(_category("keywords", "Role Keyword Relevance", [
        _check(f"{len(matched)} of {len(required)} target-profile skills found", rel, 10,
               f"Learn and add (only if genuine) skills expected for {role}: {', '.join(missing[:5])}."),
    ]))
    # 3. Education
    edu = sections.get("education", "")
    cats.append(_category("education", "Education", [
        _check("Education section present", 4 if "education" in present else 0, 4,
               "Add an 'Education' section with your degree, institution and year."),
        _check("Degree / qualification named", 3 if DEGREE_RE.search(edu or text) else 0, 3,
               "Mention your degree name clearly (e.g., B.Tech in Computer Engineering)."),
        _check("Marks, CGPA or percentage mentioned", 3 if MARKS_RE.search(edu or text) else 0, 3,
               "Add your CGPA or percentage - recruiters often filter on it."),
    ]))
    # 4. Projects
    proj = sections.get("projects", "")
    proj_lines = len([l for l in proj.splitlines() if len(l.split()) >= 4])
    proj_skills = detect_skills(proj) if proj else []
    cats.append(_category("projects", "Projects", [
        _check("Projects section present", 5 if "projects" in present else 0, 5,
               "Add a 'Projects' section with 2-3 projects you built."),
        _check(f"Project detail ({proj_lines} descriptive line(s); 4+ for full points)",
               5 if proj_lines >= 4 else (3 if proj_lines >= 2 else 0), 5,
               "Describe each project in 2-3 bullet points: problem, what you built, result."),
        _check(f"Technologies named in projects ({len(proj_skills)})",
               5 if len(proj_skills) >= 2 else (3 if proj_skills else 0), 5,
               "Name the technologies used in each project (e.g., 'Built with Flask, SQLite, Chart.js')."),
    ]))
    # 5. Experience
    lower = text.lower()
    verbs = sorted({v for v in ACTION_VERBS if re.search(r"\b" + v + r"\b", lower)})
    cats.append(_category("experience", "Work Experience", [
        _check("Experience / internship section present", 7 if "experience" in present else 0, 7,
               "Add internships, freelance work or relevant part-time roles under 'Experience'."),
        _check(f"Action verbs used ({len(verbs)}; 6+ for full points)", 8 * min(len(verbs), 6) / 6, 8,
               "Start bullet points with action verbs such as Developed, Built, Improved, Automated."),
    ]))
    # 6. Achievements & impact
    metric_text = "\n".join(v for k, v in sections.items() if k != "education")
    metrics = len(METRIC_RE.findall(metric_text))
    cats.append(_category("achievements", "Achievements & Impact", [
        _check(f"Measurable results ({metrics} number(s)/metric(s) found; 4+ for full points)", 1.5 * min(metrics, 4), 6,
               "Quantify results, e.g., 'reduced load time by 30%' or 'used by 200+ students'."),
        _check("Certifications or achievements section present",
               4 if ("certifications" in present or "achievements" in present) else 0, 4,
               "Add certifications (NPTEL, Coursera, etc.) or achievements such as hackathons."),
    ]))
    # 7. Formatting & structure
    if 250 <= words <= 900:
        length_pts = 5
    elif 150 <= words <= 1300:
        length_pts = 3
    else:
        length_pts = 1
    cats.append(_category("formatting", "Formatting & Structure", [
        _check("Email address present", 4 if info["email"] else 0, 4, "Add a professional email address at the top."),
        _check("Phone number present", 3 if info["phone"] else 0, 3, "Add your phone number at the top."),
        _check("LinkedIn or GitHub link present", 3 if (info["linkedin"] or info["github"]) else 0, 3,
               "Add your LinkedIn and GitHub profile links."),
        _check(f"Length: {words} words (250-900 is ideal)", length_pts, 5,
               "Your resume is quite short - add more detail to projects and experience (aim for 250-900 words)."
               if words < 250 else "Keep the resume to one or two pages (roughly 250-900 words)."),
        _check(f"{len(present)} standard section(s) detected (5+ for full points)", min(len(present), 5), 5,
               "Use clear standard headings: Summary, Education, Skills, Projects, Experience, Certifications."),
    ]))

    overall = round(sum(c["score"] for c in cats))
    missing_sections = [SECTION_LABELS[k] for k in SECTION_LABELS if k not in present]

    strengths, weaknesses = [], []
    for c in cats:
        if c["percent"] >= 80:
            strengths.append(f"{c['name']}: strong ({c['score']:g}/{c['max']}).")
        elif c["percent"] < 50:
            weaknesses.append(f"{c['name']}: needs work ({c['score']:g}/{c['max']}).")
    if tech_skills:
        strengths.append(f"Technical skills found in your resume: {', '.join(tech_skills[:8])}.")
    failed = sorted((ch for c in cats for ch in c["checks"] if not ch["passed"]),
                    key=lambda ch: ch["max"] - ch["points"], reverse=True)
    suggestions = []
    for ch in failed:
        if ch["tip"] not in suggestions:
            suggestions.append(ch["tip"])

    return {
        "overall_score": overall,
        "categories": cats,
        "personal_info": info,
        "sections_found": [SECTION_LABELS[k] for k in present],
        "missing_sections": missing_sections,
        "detected_skills": skills,
        "word_count": words,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions[:8],
        "recommended_skills": [s for s in missing if s not in SOFT_SKILLS][:8],
        "skill_gap": {"role": role, "company": company, "required": required, "matched": matched,
                      "missing": missing,
                      "match_percent": round(100 * len(matched) / len(required)) if required else 0},
    }


def analyze_resume(text, role, company="", use_ai=True):
    """Run the rubric, then (if configured) add AI feedback. Falls back cleanly on any AI failure."""
    result = score_resume(text, role, company)
    result["method"] = "rule"
    result["ai"] = {"used": False, "error": None}
    ai = get_ai()
    if use_ai and ai.enabled:
        try:
            feedback = ai.analyze_resume(text, result["detected_skills"], role, company, result["skill_gap"]["missing"])
            result["ai"] = {"used": True, "error": None, "model": ai.label, **feedback}
            result["method"] = "ai"
        except AIError as e:
            result["ai"] = {"used": False, "error": f"{e} Showing rule-based results only."}
    return result
