"""Job search + compatibility scoring.

Compatibility (100) = skills match 70 + experience level 15 + location 15.
Jobs come from a JobSource. Today that is the local database (sample data). To plug in a
real job API later, write another class with the same `search(filters)` method.
"""
from sqlalchemy import or_

from ..data.skills import EXPERIENCE_LEVELS
from ..models import Job, ResumeAnalysis, split_csv


class LocalJobSource:
    """Jobs stored in the SQLite database."""

    def search(self, title="", skills="", location="", experience="", job_type=""):
        q = Job.query
        if title:
            q = q.filter(or_(Job.title.ilike(f"%{title}%"), Job.description.ilike(f"%{title}%")))
        if location:
            q = q.filter(Job.location.ilike(f"%{location}%"))
        if experience:
            q = q.filter(Job.experience_level == experience)
        if job_type:
            q = q.filter(Job.job_type == job_type)
        wanted = split_csv(skills)
        if wanted:
            q = q.filter(or_(*[Job.skills.ilike(f"%{s}%") for s in wanted]))
        return q.all()


def user_skill_set(user):
    """Skills from the profile + skills detected in the user's latest analysed resume."""
    skills = list(user.profile.skill_list) if user.profile else []
    latest = (ResumeAnalysis.query.filter_by(user_id=user.id)
              .order_by(ResumeAnalysis.created_at.desc()).first())
    if latest:
        skills += latest.result.get("detected_skills", [])
    seen, out = set(), []
    for s in skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def compatibility(job, user_skills, profile):
    have = {s.lower() for s in user_skills}
    required = job.skill_list
    matched = [s for s in required if s.lower() in have]
    missing = [s for s in required if s.lower() not in have]
    skill_pts = round(70 * len(matched) / len(required)) if required else 0

    level = (profile.experience_level if profile else "") or ""
    if not level:
        exp_pts, exp_note = 8, "Experience level not set in profile (neutral score)"
    elif level == job.experience_level:
        exp_pts, exp_note = 15, "Experience level matches"
    elif (level in EXPERIENCE_LEVELS and job.experience_level in EXPERIENCE_LEVELS
          and abs(EXPERIENCE_LEVELS.index(level) - EXPERIENCE_LEVELS.index(job.experience_level)) == 1):
        exp_pts, exp_note = 8, "Experience level is close"
    else:
        exp_pts, exp_note = 0, "Experience level differs"

    prefs = split_csv(profile.preferred_locations) if profile else []
    if job.location.lower() == "remote":
        loc_pts, loc_note = 15, "Remote job"
    elif not prefs:
        loc_pts, loc_note = 8, "Preferred locations not set (neutral score)"
    elif any(p.lower() in job.location.lower() or job.location.lower() in p.lower() for p in prefs):
        loc_pts, loc_note = 15, "Matches a preferred location"
    else:
        loc_pts, loc_note = 0, "Not in your preferred locations"

    return {"score": skill_pts + exp_pts + loc_pts, "matched": matched, "missing": missing,
            "breakdown": [("Skills", skill_pts, 70, f"{len(matched)}/{len(required)} required skills"),
                          ("Experience", exp_pts, 15, exp_note), ("Location", loc_pts, 15, loc_note)]}


def ranked_jobs(user, jobs):
    skills = user_skill_set(user)
    results = [(job, compatibility(job, skills, user.profile)) for job in jobs]
    results.sort(key=lambda r: r[1]["score"], reverse=True)
    return results
